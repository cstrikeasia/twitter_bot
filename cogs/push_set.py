import discord
from discord import app_commands
from core.classes import Cog_Extension
from tweety import Twitter
import sqlite3
import os

from src.notification.account_tracker import AccountTracker
from src.permission import ADMINISTRATOR

class PushSet(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.account_tracker = AccountTracker(bot)
    
    push_group = app_commands.Group(name='push', description='設定推送', default_permissions=ADMINISTRATOR)

    @push_group.command(name='set')
    async def push_set_command(self, itn: discord.Interaction, username: str, channel: discord.TextChannel, type: str):
        """設定推送類型"""
        
        #if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
        #    return
        
        types = type.split(',')
        valid_types = ["轉發", "引用", "發佈","回覆"]
        for t in types:
            if t.strip() not in valid_types:
                await itn.response.send_message(f'無效的類型 "{t.strip()}"，請提供有效類型：轉發,引用,發佈,回覆', ephemeral=True)
                return
        
        db_path = os.path.join(os.getenv('DATA_PATH', ''), 'tracked_accounts.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user WHERE username = ?', (username,))
        match_user = cursor.fetchone()
        
        if match_user is not None:
            app = Twitter("session")
            app.load_auth_token(os.getenv('TWITTER_TOKEN'))
            try:
                new_user = app.get_user_info(username)
                
                cursor.execute('SELECT * FROM push_set WHERE id = ?', (str(channel.id),))
                existing_entry = cursor.fetchone()
                
                if existing_entry:
                    cursor.execute('UPDATE push_set SET username = ?, type = ? WHERE id = ?', (username, type, str(channel.id)))
                else:
                    cursor.execute('INSERT INTO push_set (id, username, type) VALUES (?, ?, ?)', (str(channel.id), username, type))
                
                conn.commit()
                description = f"```{type}```"
                embed = discord.Embed(
                    title="成功設定推送類型",
                    description=description,
                    color=0x778899
                )

                await itn.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                print(e)
                await itn.followup.send(f'未找到{username}', ephemeral=True)
                return
        else:
            await itn.followup.send('未找到此用戶', ephemeral=True)
        
        conn.close()

async def setup(bot):
    await bot.add_cog(PushSet(bot))