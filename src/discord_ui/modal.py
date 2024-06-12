import discord
import os
import sqlite3

class CustomizeMsgModal(discord.ui.Modal, title='自訂通知訊息'):
    def __init__(self, user_id: str, username: str, channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.channel = channel
        label = f'在#{channel.name}為@{username}設定自訂通知訊息'
        if len(label) > 45: label = f'為@{username}設定自訂通知訊息'
        if len(label) > 45: label = f'自訂通知訊息'
        self.customized_msg = discord.ui.TextInput(label=label, placeholder='輸入自訂通知訊息', max_length=200, style=discord.TextStyle.long, required=True)
        self.add_item(self.customized_msg)

    async def on_submit(self, itn: discord.Interaction):
        await itn.response.defer(ephemeral=True)
        
        conn = sqlite3.connect(f"{os.getenv('DATA_PATH')}tracked_accounts.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('UPDATE notification SET customized_msg = ? WHERE user_id = ? AND channel_id = ?', (self.customized_msg.value, self.user_id, str(self.channel.id)))
        conn.commit()
        conn.close()
        
        await itn.followup.send('設定成功', ephemeral=True)