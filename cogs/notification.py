import discord
from discord import app_commands
from core.classes import Cog_Extension
from tweety import Twitter
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
import sqlite3

from src.log import setup_logger
from src.notification.account_tracker import AccountTracker
from src.discord_ui.modal import CustomizeMsgModal
from src.permission import ADMINISTRATOR
from configs.load_configs import configs

log = setup_logger(__name__)

load_dotenv()

class Notification(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.account_tracker = AccountTracker(bot)

    add_group = app_commands.Group(name='add', description='新增些什麼', default_permissions=ADMINISTRATOR)
    remove_group = app_commands.Group(name='remove', description='刪除些什麼', default_permissions=ADMINISTRATOR)
    customize_group = app_commands.Group(name='customize', description='自訂些什麼', default_permissions=ADMINISTRATOR)

    def check_block(self, cursor, server_id: str) -> bool:
        """檢查是否已經被禁用"""
        cursor.execute("""
            SELECT server_id
            FROM block
            WHERE server_id = ?
        """, (server_id,))
        check_block_data = cursor.fetchone()
        if check_block_data:
            return True
        return False
        
    @add_group.command(name='notifier')
    async def notifier(self, itn : discord.Interaction, username: str, channel: discord.TextChannel, mention: discord.Role = None):
        """將Twitter用戶新增至伺服器上的特定頻道

        Parameters
        -----------
        username: str
            想要開啟通知的Twitter用戶的用戶名
        channel: discord.TextChannel
            機器人發送通知的管道
        mention: discord.Role
            通知時要提及的角色(可選填)
        """
        
        #if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
        #    return
        
        await itn.response.defer(ephemeral=True)
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user WHERE username = ?', (username,))
        match_user = cursor.fetchone()
        
        server_id = str(channel.guild.id)
        server_name = channel.guild.name
        roleID = str(mention.id) if mention != None else ''
        
        #if self.check_block(cursor, server_id):
        #    await itn.followup.send(f'您沒有權限使用此指令', ephemeral=True)
        #    return
            
        if match_user == None or match_user['enabled'] == 0:
            app = Twitter("session")
            app.load_auth_token(os.getenv('TWITTER_TOKEN'))
            try:
                new_user = app.get_user_info(username)
            except:
                await itn.followup.send(f'無法找到{username}', ephemeral=True)
                return
            
            if match_user == None:
                cursor.execute('INSERT INTO user (id, username, lastest_tweet) VALUES (?, ?, ?)', (str(new_user.id), username, datetime.utcnow().replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M:%S%z')))
                cursor.execute('INSERT OR IGNORE INTO channel VALUES (?, ?, ?)', (str(channel.id), server_id, server_name))
                cursor.execute('INSERT INTO notification (user_id, channel_id, role_id) VALUES (?, ?, ?)', (str(new_user.id), str(channel.id), roleID))
            else:
                cursor.execute('INSERT OR IGNORE INTO channel VALUES (?, ?, ?)', (str(channel.id), server_id, server_name))
                cursor.execute('REPLACE INTO notification (user_id, channel_id, role_id) VALUES (?, ?, ?)', (match_user['id'], str(channel.id), roleID))
                cursor.execute('UPDATE user SET enabled = 1 WHERE id = ?', (match_user['id'],))
                
            
            app.follow_user(new_user)
            
            if app.enable_user_notification(new_user): log.info(f'已成功將{username}開啟通知')
            else: log.warning(f'無法將{username}開啟通知')
        else:
            cursor.execute('INSERT OR IGNORE INTO channel VALUES (?, ?, ?)', (str(channel.id), server_id, server_name))
            cursor.execute('REPLACE INTO notification (user_id, channel_id, role_id) VALUES (?, ?, ?)', (match_user['id'], str(channel.id), roleID))
        
        conn.commit()
        conn.close()
            
        if match_user == None or match_user['enabled'] == 0: await self.account_tracker.addTask(username)
            
        await itn.followup.send(f'成功將{username}加入通知', ephemeral=True)


    @remove_group.command(name='notifier')
    async def notifier(self, itn : discord.Interaction, username: str, channel: discord.TextChannel):
        """刪除伺服器上的通知

        Parameters
        -----------
        username: str
            想要關閉通知的Twitter用戶的用戶名
        channel: discord.TextChannel
            設定發送通知的頻道
        """
        
        #if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
        #    return
        
        await itn.response.defer(ephemeral=True)
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM notification, user WHERE username = ? AND channel_id = ? AND user_id = id AND notification.enabled = 1', (username, str(channel.id)))
        match_notifier = cursor.fetchone()
        if match_notifier != None:
            cursor.execute('UPDATE notification SET enabled = 0 WHERE user_id = ? AND channel_id = ?', (match_notifier['user_id'], str(channel.id)))
            conn.commit()
            await itn.followup.send(f'成功將{username}從通知列表刪除', ephemeral=True)
            cursor.execute('SELECT user_id FROM notification WHERE user_id = ? AND enabled = 1', (match_notifier['user_id'],))
            
            if len(cursor.fetchall()) == 0:
                cursor.execute('UPDATE user SET enabled = 0 WHERE id = ?', (match_notifier['user_id'],))
                conn.commit()
                await self.account_tracker.removeTask(username)
                if configs['auto_unfollow'] or configs['auto_turn_off_notification']:
                    app = Twitter("session")
                    app.load_auth_token(os.getenv('TWITTER_TOKEN'))
                    target_user = app.get_user_info(username)
                    
                    if configs['auto_unfollow']: 
                        log.info(f'已成功取消關注{username}') if app.unfollow_user(target_user) else log.warning(f'無法取消關注{username}')
                    else:
                        log.info(f'已成功關閉通知{username}') if app.disable_user_notification(target_user) else log.warning(f'無法對{username}關閉通知')
                
        else:
            await itn.followup.send(f'在{channel.mention}中找不到通知者{username}', ephemeral=True)
        
        conn.close()
        
        
    @customize_group.command(name='message')
    async def customize_message(self, itn : discord.Interaction, username: str, channel: discord.TextChannel, default: bool = False):
        """設定通知的自訂訊息

        Parameters
        -----------
        username: str
            要設定自訂訊息的Twitter用戶的使用者名稱
        channel: discord.TextChannel
            設定發送通知的頻道
        default: bool
            是否使用預設設定
        """
        
        #if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
        #    return
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM notification, user WHERE username = ? AND channel_id = ? AND user_id = id AND notification.enabled = 1', (username, str(channel.id)))
        match_notifier = cursor.fetchone()
        if match_notifier != None:
            if default:
                await itn.response.defer(ephemeral=True)
                cursor.execute('UPDATE notification SET customized_msg = ? WHERE user_id = ? AND channel_id = ?', (None, match_notifier['user_id'], str(channel.id)))
                conn.commit()
                await itn.followup.send('成功恢復預設設定', ephemeral=True)
            else:
                modal = CustomizeMsgModal(match_notifier['user_id'], username, channel)
                await itn.response.send_modal(modal)
        else:
            await itn.response.send_message(f'在{channel.mention}中找不到通知者{username}', ephemeral=True)
            
        conn.close()


async def setup(bot):
	await bot.add_cog(Notification(bot))