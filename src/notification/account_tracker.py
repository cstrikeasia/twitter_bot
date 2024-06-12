import discord
from tweety import Twitter
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import sqlite3
import asyncio

from src.log import setup_logger
from src.notification.display_tools import gen_embed, get_action
from src.notification.get_tweets import get_tweets
from src.db_function.db_executor import execute
from configs.load_configs import configs

log = setup_logger(__name__)

load_dotenv()

class AccountTracker():
    def __init__(self, bot):
        self.bot = bot
        self.tasksMonitorLogAt = datetime.utcnow() - timedelta(seconds=configs['tasks_monitor_log_period'])
        bot.loop.create_task(self.setup_tasks())

    async def setup_tasks(self):
        app = Twitter("session")
        app.load_auth_token(os.getenv('TWITTER_TOKEN'))
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        cursor = conn.cursor()
        
        self.bot.loop.create_task(self.tweetsUpdater(app)).set_name('TweetsUpdater')
        cursor.execute('SELECT username FROM user WHERE enabled = 1')
        usernames = []
        for user in cursor:
            username = user[0]
            usernames.append(username)
            self.bot.loop.create_task(self.notification(username)).set_name(username)
        self.bot.loop.create_task(self.tasksMonitor(set(usernames))).set_name('TasksMonitor')
        
        conn.close()

    def check_block(self, cursor, channel_id: str) -> bool:
        """檢查是否已經被禁用"""
        cursor.execute("""
            SELECT COUNT(*)
            FROM block
            JOIN channel ON block.server_id = channel.server_id
            WHERE channel.id = ?
        """, (channel_id,))
        return cursor.fetchone()[0] > 0
        
    async def notification(self, username):
        while True:
            await asyncio.sleep(configs['twitter_check_period'])

            task = asyncio.create_task(asyncio.to_thread(get_tweets, self.tweets, username))
            await task
            lastest_tweets = task.result()
            if lastest_tweets == None: continue
            
            conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            user = cursor.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
            execute(conn, 'UPDATE user SET lastest_tweet = ? WHERE username = ?', (str(lastest_tweets[-1].created_on), username), username)
            for tweet in lastest_tweets:
                log.info(f'尋找來自{username}的新推文')
                for data in cursor.execute('SELECT * FROM notification WHERE user_id = ? AND enabled = 1', (user['id'],)):
                    channel = self.bot.get_channel(int(data['channel_id']))
                    conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    """查詢被禁用的頻道(伺服器)，如果在禁用資料庫內，就不會發送訊息到該頻道"""
                    if self.check_block(cursor, int(data['channel_id'])):
                        continue

                    if channel != None:
                        try:
                            mention = f"{channel.guild.get_role(int(data['role_id'])).mention} " if data['role_id'] != '' else ''
                            author, action, url = tweet.author.name, get_action(tweet), tweet.url
                            
                            if not self.check_channel_exists(cursor, int(data['channel_id']), author, action):
                                continue
                                
                            msg = ("***{author}*** " + data['customized_msg']) if data['customized_msg'] else "**{author}**剛剛{action}"
                            msg = msg.format(mention=mention, author=author, action=action, url=url)
                            await channel.send(msg, file = discord.File('images/twitter.png', filename='twitter.png'), embeds = gen_embed(tweet))
                        except Exception as e:
                            print(e)
                            if not isinstance(e, discord.errors.Forbidden): log.error(f'發送通知時，{channel.mention}發生意外錯誤')
                    
            conn.close()

    def check_channel_exists(self, cursor, channel_id, author, action):
        """檢查頻道是否存在於資料庫中，並且類型包含指定的action"""
        query = 'SELECT COUNT(*) FROM push_set WHERE id = ? AND type LIKE ?'
        result = cursor.execute(query, (channel_id, f'%{action}%')).fetchone()
        return result[0] > 0


    async def tweetsUpdater(self, app):
        while True:
            try: self.tweets = app.get_tweet_notifications()
            except Exception as e:
                log.error(f'{e} (task : tweets updater)')
                log.error(f"發生意外錯誤，請在{configs['update_retry_delay'] / 60}分鐘後重試")
                await asyncio.sleep(configs['update_retry_delay'])
            await asyncio.sleep(configs['twitter_check_period'])


    async def tasksMonitor(self, users : set):
        while True:
            taskSet = {task.get_name() for task in asyncio.all_tasks()}
            aliveTasks = taskSet & users
            
            if aliveTasks != users:
                deadTasks = list(users - aliveTasks)
                log.warning(f'dead tasks : {deadTasks}')
                for deadTask in deadTasks:
                    self.bot.loop.create_task(self.notification(deadTask)).set_name(deadTask)
                    log.info(f'成功重啟{deadTask}')
                
            if 'TweetsUpdater' not in taskSet:
                log.warning('tweets updater : dead')
                
            if (datetime.utcnow() - self.tasksMonitorLogAt).total_seconds() >= configs['tasks_monitor_log_period']:
                log.info(f'alive tasks : {list(aliveTasks)}')
                if 'TweetsUpdater' in taskSet: log.info('tweets updater : alive')
                self.tasksMonitorLogAt = datetime.utcnow()
                
            await asyncio.sleep(configs['tasks_monitor_check_period'])
            

    async def addTask(self, username : str):
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        cursor = conn.cursor()
        
        self.bot.loop.create_task(self.notification(username)).set_name(username)
        log.info(f'new task {username} added successfully')
        
        for task in asyncio.all_tasks():
            if task.get_name() == 'TasksMonitor':
                try: log.info(f'現有TasksMonitor已關閉') if task.cancel() else log.info('現有TasksMonitor無法關閉')
                except Exception as e: log.warning(f'addTask : {e}')
        self.bot.loop.create_task(self.tasksMonitor({user[0] for user in cursor.execute('SELECT username FROM user WHERE enabled = 1').fetchall()})).set_name('TasksMonitor')
        log.info(f'新的TasksMonitor已啟動')
        
        conn.close()
        

    async def removeTask(self, username : str):
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        cursor = conn.cursor()
        
        for task in asyncio.all_tasks():
            if task.get_name() == 'TasksMonitor':
                try: log.info(f'現有TasksMonitor已關閉') if task.cancel() else log.info('現有TasksMonitor無法關閉')
                except Exception as e: log.warning(f'removeTask : {e}')
                
        for task in asyncio.all_tasks():
            if task.get_name() == username:
                try: log.info(f'現有任務{username}已關閉') if task.cancel() else log.info(f'現有任務{username}無法關閉')
                except Exception as e: log.warning(f'removeTask : {e}')
        
        self.bot.loop.create_task(self.tasksMonitor({user[0] for user in cursor.execute('SELECT username FROM user WHERE enabled = 1').fetchall()})).set_name('TasksMonitor')
        log.info(f'新的TasksMonitor已啟動')
        
        conn.close()