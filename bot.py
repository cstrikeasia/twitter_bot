import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os

from src.log import setup_logger
from src.db_function.init_db import init_db
from configs.load_configs import configs

log = setup_logger(__name__)

load_dotenv()

bot = commands.Bot(command_prefix=configs['prefix'], intents=discord.Intents.all())


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=configs['activity']))
    if not(os.path.isfile(f"{os.getenv('DATA_PATH')}tracked_accounts.db")): init_db()
    bot.tree.on_error = on_tree_error
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
    log.info(f'{bot.user} is online')
    slash = await bot.tree.sync()
    log.info(f'成功同步{len(slash)}個斜線指令')


@bot.command()
@commands.is_owner()
async def load(ctx, extension):
    await bot.load_extension(f'cogs.{extension}')
    await ctx.send(f'載入{extension}完成。')


@bot.command()
@commands.is_owner()
async def unload(ctx, extension):
    await bot.unload_extension(f'cogs.{extension}')
    await ctx.send(f'卸載 - 載入{extension}完成。')


@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    await bot.reload_extension(f'cogs.{extension}')
    await ctx.send(f'重載 - 載入{extension}完成。')

@bot.command()
@commands.is_owner()
async def download_log(ctx : commands.context.Context):
    message = await ctx.send(file=discord.File('console.log'))
    await message.delete(delay=15)

@bot.command()
@commands.is_owner()
async def download_data(ctx : commands.context.Context):
    message = await ctx.send(file=discord.File(f"{os.getenv('DATA_PATH')}tracked_accounts.db"))
    await message.delete(delay=15)


@bot.command()
@commands.is_owner()
async def upload_data(ctx : commands.context.Context):
    raw = await [attachment for attachment in ctx.message.attachments if attachment.filename[-3:] == '.db'][0].read()
    with open(f"{os.getenv('DATA_PATH')}tracked_accounts.db", 'wb') as wbf:
        wbf.write(raw)
    message = await ctx.send('數據上傳成功')
    await message.delete(delay=5)


@bot.event
async def on_tree_error(itn : discord.Interaction, error : app_commands.AppCommandError):
    await itn.response.send_message(error, ephemeral=True)
    log.warning(f'發生錯誤，但已由tree錯誤處理程序處理，錯誤訊息：{error}')


@bot.event
async def on_command_error(ctx : commands.context.Context, error : commands.errors.CommandError):
    if isinstance(error, commands.errors.CommandNotFound): return
    else: await ctx.send(error)
    log.warning(f'發生錯誤，但已由指令錯誤處理程序處理，錯誤訊息：{error}')


if __name__ == '__main__':
    bot.run(os.getenv('BOT_TOKEN'))
