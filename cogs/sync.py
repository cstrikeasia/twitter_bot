import discord
from discord import app_commands
from core.classes import Cog_Extension
from dotenv import load_dotenv
import os
import sqlite3

from src.log import setup_logger
from src.sync_db.sync_db import sync_db

log = setup_logger(__name__)

load_dotenv()

class Sync(Cog_Extension):

    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name='sync')
    async def sync(self, itn : discord.Interaction):
        """如果要將新Twitter帳戶的通知與資料庫同步可使用此指令"""
        
        if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
            return
        
        await itn.response.defer(ephemeral=True)
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user')
        follow_list = cursor.fetchall()
        
        conn.commit()
        conn.close()
        
        self.bot.loop.create_task(sync_db(follow_list))
            
        await itn.followup.send(f"成功在後台同步", ephemeral=True)


async def setup(bot):
	await bot.add_cog(Sync(bot))