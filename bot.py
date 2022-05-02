import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient
import logging
import random

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

mongoURL = open("mongo-url.txt", "r").read()
cluster = MongoClient(mongoURL)


###################
# Counting stuff #
#################

db = cluster["Counting"]
collection = db["config"]

#Check if Counting Channel is Configured
myquery = { "_id": 1 }

# Global Variables - Not the coolest, but we're trying for now
countingChannelId = None
currentCount = None
countingTarget = None
lastCounter = None

# Check if the config is generated in the DB, if so pull the values out and these should be stored in the global variables
if (collection.count_documents(myquery) != 0):
    document = collection.find_one({"_id":1})

    countingChannelId = document["channel-id"]
    currentCount = document["currentCount"]
    countingTarget = document["countTarget"]
    lastCounter = document["lastCounter"]

    # Print Values to console
    print(f"Counting Channel configuration found.")
    print(f"Counting Channel ID: {countingChannelId}")
    print(f"currentCount: {currentCount}")
    print(f"countingTarget: {countingTarget}")
    print(f"lastCounter: {lastCounter}")
#End of Counting Config

token = open("token.txt", "r").read()
client = discord.Client()
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    await client.get_channel(countingChannelId).send(f"{(random.choice(list(open('spawn-gifs.txt'))))}")
    await client.get_channel(countingChannelId).send(f"I'm back! We're picking it back up at {currentCount}. Somone gimme a {currentCount}!")

@client.event
async def on_message(ctx): 
    print(f"{ctx.channel}: {ctx.author}: {ctx.author.name}: {ctx.content}")

    ######################################
    # Start of Counting Channel Commands #
    ######################################
    global currentCount
    global countingTarget
    global lastCounter
    db = cluster["Counting"]
    collection = db["config"]

    # Set the Counting Channel
    if "!rage set counting channel" in str(ctx.content):
        if ctx.author.guild_permissions.administrator:
            print(f'Setting Counting Channel to {ctx.channel.id}')
            post = {"_id": 1, "channel-id": ctx.channel.id, "channel-name": ctx.channel.name, "currentCount": 0, "countTarget": random.randint(1,10)}
            collection.insert_one(post)
            await ctx.channel.send(f'Set {ctx.channel.name} as the counting Channel!')
            return
        else:
            print('Only an admin can do that.')
            return
    
    # Check if incoming message is on Counting Channel
    if ctx.channel.id == countingChannelId: 
        # Check if the incoming message is a digit only
        if ctx.content.isdigit(): #
            newNumber = int(ctx.content) # New number from discord user
            
            # Check if the new number matches the currentCount Number
            if newNumber == int(currentCount):

                # Log to console Discord ID of lastCounter (person who last counted a correct number)
                print(f"lastCounter: {lastCounter}")
                # Log to console Discord ID of current Discord user to count
                print(f"currentCounter: {ctx.author.display_name}({ctx.author.id})")

                # Proceed if the current discord user ID doesn't match lastCounter ID
                if int(ctx.author.id) != int(lastCounter):
                    #Make the current counter new lastCounter
                    lastCounter = ctx.author.id
                    collection.update_one({"_id":1}, {"$set":{"lastCounter":ctx.author.id}})

                    # Check if newNumber from Discord user equals the winning target number
                    if countingTarget == newNumber:
                        
                        # Target was reached, generate a new target number
                        newTarget = random.randint(0,100)
                        # Write values to the db for new countTarget, reset current count to 0, and set the lastCounter id.
                        collection.update_one({"_id":1}, {"$set":{"countTarget":newTarget, "currentCount":0, "lastCounter":ctx.author.id}})
                        
                        collection = db["UserData"]
                        myquery = { "_id": ctx.author.id }
                        if (collection.count_documents(myquery) != 0):
                            document = collection.find_one({"_id":ctx.author.id})
                            userScore = document["score"] + 1
                            collection.update_one({"_id":ctx.author.id}, {"$set":{"score":userScore}})
                        else:
                            post = {"_id": ctx.author.id, "score": 1}
                            collection.insert_one(post)
                            userScore = 1

                        await ctx.channel.send(f"{(random.choice(list(open('goose-gifs.txt'))))}")
                        await ctx.channel.send(f"{ctx.author.mention} Congratulations you are now the holder of the silly goose!")
                        await ctx.channel.send(f"You have won {userScore} times!") # TODO - store number of wins
                        await ctx.channel.send(f"Counting will now start over. I'm a computer - so start at 0!")

                        currentCount = 0
                        countingTarget = newTarget
                        return

                    # if newNumber from Discord user does not equal target number
                    else:
                        #increment the currentCount number and write it to the DB
                        currentCount += 1
                        collection.update_one({"_id":1}, {"$set":{"currentCount":currentCount}})
                        return
                
                # If the current discord user ID is the same as the previous, they need to wait for someone else to go
                else:
                        await ctx.channel.send(f"It's not your turn! Wait for somebody else to go!")
                        return
            
            # If the newNumber from discord user does not equal the expected number, reject it.
            elif newNumber != currentCount:
                await ctx.channel.send(f"Bleep. Bloop. Does not compute. Try again!")
                print(f"bad. Your number: {newNumber} Current Number: {currentCount}")
                return
        if ctx.content.lower().startswith('!leaderboard'):
            # TODO - Build leaderboard command to list player scores
                # Pull top 10 scores from DB & list player names and scores in order
            return

    if ctx.content.lower() == 'hello':
        await ctx.channel.send(f'Hello, {ctx.author.display_name}!')
        return

    if ctx.content.lower().startswith('!roll'):
        if ctx.content.lower() == '!roll':
            await ctx.channel.send(f"Try d4, d6, d8, d10, d12, or d20")
            await ctx.channel.send(f"example: !roll d20 or !roll 3xd8")

        roll = ctx.content.lower().replace(" ", "")[5:]
        d = roll.split('d',1)[1]
        x = 1 # Default Multiplier is 1
        if roll[0].isdigit():
            x = roll[0]
        if d in ('4', '6', '8', '10', '12', '20'):
            count = 0
            result = 0
            while count < int(x):
                result += random.randint(1,int(d))
                count += 1
            await ctx.channel.send(f'{result}')
        else:
            await ctx.channel.send(f"{(random.choice(list(open('rejected-gifs.txt'))))}")
            await ctx.channel.send(f"Only d4, d6, d8, d10, d12, or d20 accepted")

        # ToDo take valid dice rolls D4, D6, D8, D10, D12, D20
        # Be able to roll multiple dice. example: !roll 2xd6

client.run(token)