import discord
from discord import app_commands
from core.classes import Cog_Extension
import sqlite3
import os

from src.permission import ADMINISTRATOR

class ServerManager(Cog_Extension):
    
    server_group = app_commands.Group(name='server', description='管理伺服器', default_permissions=ADMINISTRATOR)

    @server_group.command(name='list')
    async def list_servers(self, itn: discord.Interaction):
        """列出該機器人在所有伺服器註冊服務的資訊"""
        
        if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
            return
        
        db_path = os.path.join(os.getenv('DATA_PATH', ''), 'tracked_accounts.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, server_id, server_name
            FROM channel
        """)
        server_channel_data = cursor.fetchall()

        conn.close()

        server_list = [f"伺服器:{server_name} ({server_id})\n頻道:<#{id}>\n" for id, server_id, server_name in server_channel_data]
        
        description = '\n'.join(server_list) if server_list else "***沒有伺服器使用此服務***"
        
        embed = discord.Embed(
            title="已註冊服務伺服器列表",
            description=description,
            color=0x778899
        )

        await itn.response.send_message(embed=embed, ephemeral=True)

    @server_group.command(name='ban')
    async def block_server(self, itn: discord.Interaction, serverid: str):
        """禁用指定的伺服器"""
        
        if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
            return
        
        db_path = os.path.join(os.getenv('DATA_PATH', ''), 'tracked_accounts.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT 1 FROM block WHERE server_id = ?", (serverid,))
            if cursor.fetchone():
                await itn.response.send_message(f"***{serverid}***已經被禁用", ephemeral=True)
                return
            
            cursor.execute("INSERT INTO block (server_id) VALUES (?)", (serverid,))
            conn.commit()
            
            cursor.execute("""
                SELECT server_name
                FROM channel
                WHERE server_id = ?
            """, (serverid,))
            server_data = cursor.fetchone()
            
            if server_data:
                server_name = server_data[0]
                await itn.response.send_message(f"成功禁用***{server_name}***", ephemeral=True)
        except sqlite3.IntegrityError as e:
            await itn.response.send_message(f"無法禁用***{serverid}***，錯誤: {str(e)}", ephemeral=True)
        finally:
            conn.close()
            
    @server_group.command(name='unban')
    async def unblock_server(self, itn: discord.Interaction, serverid: str):
        """解除禁用指定的伺服器"""
        
        if itn.user.name != os.getenv('ADMIN_ID'): #僅限管理員使用指令
            return
        
        db_path = os.path.join(os.getenv('DATA_PATH', ''), 'tracked_accounts.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT 1 FROM block WHERE server_id = ?", (serverid,))
            if not cursor.fetchone():
                await itn.response.send_message(f"***{server_id}***尚未被禁用", ephemeral=True)
                return
            
            cursor.execute("DELETE FROM block WHERE server_id = ?", (serverid,))
            conn.commit()
            
            cursor.execute("""
                SELECT server_name
                FROM channel
                WHERE server_id = ?
            """, (serverid,))
            server_data = cursor.fetchone()
            
            if server_data:
                server_name = server_data[0]
                await itn.response.send_message(f"成功解除禁用***{server_name}***", ephemeral=True)
        except sqlite3.IntegrityError as e:
            await itn.response.send_message(f"無法解除禁用伺服器***{serverid}***，錯誤: {str(e)}", ephemeral=True)
        finally:
            conn.close()
            
async def setup(bot):
    await bot.add_cog(ServerManager(bot))