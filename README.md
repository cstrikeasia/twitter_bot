- Author: Yuuzi261
- Secondary Development:miyashooooo
- This robot can be set up directly on the host, and then let the server to use this service to invite the robot into the group can be
- Do not modify the ```DATA_PATH``` if it is not necessary.

## start
```pip install -r requirements.txt```
install the necessary modules

```python bot.py```
Run and invite the bot to your server

[.env]

```BOT_TOKEN```
discord bot token

```TWITTER_TOKEN```
Twitter login COOKIE (install the Chrome plugin https://www.editthiscookie.com to get, after installation into the Twitter random page, click please refer to the image folder [cookie取得教學_1, cookie取得教學_2])

```DATA_PATH```
data path

```ADMIN_ID```
Admin discord id

-------------------------

[Bot Commands]

#admin

```/server list```
View a list of servers that have registered for this service

```/server ban [Server ID] ```
Disables the specified server from using this service, so that it does not receive subscription notifications

```/server unban [Server ID]```
Undisable the specified server to use this service, the server can receive subscribed notification messages after it is undisabled

```/sync```
Synchronize Twitter notifications with the database


#Users

```/add notifier [Twitter Username] [Channel ID] [Users to tag (optional)]```
Add users to receive notifications

```/remove notifier [Twitter Username] [Channel ID] ```
Remove users to receive notifications

```/customize message [Twitter Username] [Channel ID] [Customize push message (True to restore initial settings, False to set custom message)]```
Customizing notification messages

```/list users```
List the push username that are currently registered to receive notifications on the server

```/push set ```
Set the type of push notifications to receive (發佈,轉發,引用,回覆), separated by commas, so that when a notifier publishes, quotes, or forwards a message, it will not send it if it is not in the list
