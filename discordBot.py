from discord import channel
from DeepScout import scout
from typing import Counter
from sqlalchemy import create_engine
from discord.ext import commands
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import discord
import squarify
import matplotlib
import os
import requests
import time
import pandas as pd

# TODO : 
# Make all the functions coroutines
# Replaces the squares and names by champion images
# Use commands instead of messages
# Add a timestamp argument
# add a teamscouts
# upload on heroku


load_dotenv()


token = open("data/DiscordToken.txt", "r").readline()
isRunning = False
client = discord.Client()
history = []
chan =discord.channel
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)
pwd = open("data/DB_login.txt", "r").readline()


sqlEngine       = create_engine('mysql+pymysql://root:'+pwd+'@localhost/lol_champ_pool')
dbConnection    = sqlEngine.connect()

pseudo = ""
account_puuid = ""

# Defining our API key
secret = open("data/API_Key.txt", "r").readline()

# Headers for all our requests
headers = {
    'X-Riot-Token':secret
}


def makeRequest(request, header):
    global history

    now = time.time()
    # print("now : " +str(now))
    if len(history)>50:

        
        while len(history)>10 and (history[0] < (time.time() - 120)):
            history.pop(0)
  

    if len(history) >= 98:
        print("sleeping for " + str(history[0]-(now-120)) + " seconds")

        time.sleep(history[0]-(now-120))
          
    history.append(now)
    # print("request")
    return requests.get(request, headers=header)

def find(playerPseudo):
    global pseudo
    global account_puuid
    global chan
    found = False
    
    

    # Retrieve the arg (player pseudo)
    target = playerPseudo

    # Check if we alrload("diag")$eady have the puuid and case-sensitive pseudo, other wise do the request
    # PlayerList data format: pseudo;puuid

    find = False
    try: 
        playerList = pd.read_sql_table("Playerlist", dbConnection)
        
    except ValueError as vx:

        print(vx)
        playerList = pd.DataFrame(data=None)

    else:
        print("player list : ")
        print(playerList)  
        for p in playerList.itertuples(index=False):
            name=p[0]

            if playerPseudo.casefold() == name.casefold():
                pseudo = name
                account_puuid = p[1]
                find = True
                break

    if find == False:
        print("Player isn't in database, starting requests...")
        #sendMessage("Player isn't in database, loading games for the first time can be long", chan)
        reponse = makeRequest("https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + target, headers)
        if reponse.status_code == 200:
            reponse = reponse.json()
            pseudo = reponse["name"]
            account_puuid = reponse["puuid"]
            playerinfo = pd.Series({'pseudo':pseudo, 'puuid': account_puuid})
            playerList = playerList.append(playerinfo, ignore_index=True)
            playerList.to_sql("Playerlist", dbConnection, if_exists='replace', index=False, index_label=["puuid"])
        elif reponse.status_code == 404:
            #sendMessage("Incorrect pseudo, player not found")
            return 404
            
    
            

        account_puuid = account_puuid.removesuffix("\n")

    if find:
        return 1
    else:
        return 0


def printTreeMap(df):

        labels = df["Champion"].tolist()
        played = df["Played"].tolist()  
        wins = df["Wins"].tolist()

        # size = [sub_list[2] for sub_list in values]
        # labels = [sub_list[0] for sub_list in values]
        # vals = [sub_list[1] for sub_list in values]

        # print(labels)
        # print(played)
        # print(wins)

        colors = []
        wr = []
        for i in range(len(played)):
            # print(wins[i])
            # print(played[i])
            if ((wins[i]/played[i]) > 0.5):
                c = "green"
            elif wins[i]/played[i] < 0.5:
                c = "red"
            else:
                c = "blue"
            colors.append(c)
            wr.append(wins[i]/played[i])
            
        # print(wr)

        cmap = matplotlib.cm.RdYlGn
        mini = 0.3
        maxi = 0.7
        norm = matplotlib.colors.Normalize(vmin=mini, vmax=maxi)
        c2 = [cmap(norm(value)) for value in wr]

        plt.clf()
        squarify.plot(played,pad = True,label = labels, color=c2)
        plt.axis("off")
         

        plt.savefig("temp/discordPrint.png")
        # plt.show()
        # return plt    

def scout(target):
    global pseudo
    global account_puuid

    
    print("pseudo : " + pseudo)


    # Read the file
    try: 
        regGames = pd.read_sql_table(pseudo, dbConnection)
        
    except ValueError as vx:
        print(vx)
        regGames = pd.DataFrame(data=None)
        regGamesList = []
    else:
        print(str(len(regGames)) + " games found in database")
        regGamesList = regGames["MatchID"].tolist()
    

    #regGames = pd.read_csv("data/" + pseudo + ".csv", sep=",", names=["Timestamp", "MatchID", "Champion", "Win"])
    
    print(" Found "+str(len(regGamesList))+" games in database")

    # Retrieve a list of the last 50 games played
    newGamesList = makeRequest("https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/"+account_puuid + "/ids?type=ranked&start=0&count=90", headers).json()


    # Keep only thoses who aren't in the file
    gamesToSearch = list((Counter(newGamesList)-Counter(regGamesList)).elements())


    print(" Retrieving "+str(len(gamesToSearch))+" games from Riot API")
    n =90

    endSearch = False

    while(endSearch == False):

        for g in gamesToSearch:

            gameInfo = makeRequest("https://europe.api.riotgames.com/lol/match/v5/matches/"+g, headers).json()
            participantInfos = gameInfo["info"]["participants"]
            for player in participantInfos:
                if player["puuid"] == account_puuid:
                    dataToAdd = {'Timestamp':int(gameInfo["info"]["gameCreation"]),'MatchID':g,'Champion':player["championName"],'Win':int(player["win"])}
                    gameToAdd = pd.Series(data=dataToAdd, index=None)
                    
                    print("Adding game " + g + " : " + player["championName"] + ", Win = "+ str(player["win"]) )
                    regGames = regGames.append(gameToAdd, ignore_index=True)
                    # print("added, regGames :")
                    # print(regGames)
                    
                    # if(regGames.size !=0):
                    #     regGames = np.vstack ((regGames, gameToAdd))
                    # else:
                    #     regGames = np.append(regGames,np.array([int(gameInfo["info"]["gameCreation"]),g,player["championName"],int(player["win"])]), axis=0)
        
        endSearch = False
        regGamesList = regGames["MatchID"].tolist()

        gamesToSearch = list((Counter(newGamesList)-Counter(regGamesList)).elements())
        #print("Lenght Games to search = " + str(len(gamesToSearch)))

        while(endSearch == False and len(gamesToSearch)==0):
            print("n = "+ str(n))
            rq = makeRequest("https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/"+account_puuid + "/ids?type=ranked&start="+str(n)+"&count=90", headers)
            newGamesList = rq.json()
            regGamesList = regGames["MatchID"].tolist()
            if(len(newGamesList) == 0):
                print("NewGameList is empty")
                endSearch = True
            rqNumber = int(rq.headers["X-App-Rate-Limit-Count"].split(",")[1].split(":")[0])
            gamesToSearch = list((Counter(newGamesList)-Counter(regGamesList)).elements())
            print("Lenght Games to search = " + str(len(gamesToSearch)))
            print("Request number : " + str(rqNumber))
            n += 90

        # print(gamesToSearch)
        # print(len(gamesToSearch))
        # print("Request number : " + str(rqNumber))
        #to avoid being blocked by the API rate limit
        # if(len(gamesToSearch)+rqNumber>95):
        #     print("Charging additional games, waiting 120 seconds because of the fucking API limit rate")
        #     time.sleep(120)

    print("Game Histroy : ")
    print(regGames)
    regGames.to_sql(pseudo, dbConnection, if_exists='replace', index=False, index_label=["Timestamp"])
    #regGames.to_csv("data/" + pseudo + ".csv", index=False, header=False)
    print("Game History saved into database")

    playedChamps = pd.DataFrame(columns=["Champion","Wins","Played"])

    print("building the champ pool...")
    for row in regGames.itertuples(index=False):
        # print(row)
        champ = row[2]
        win = row[3]
        index = playedChamps.index[playedChamps['Champion']==champ]
        # print("index : ")
        # print(index)
        if  len(index)==1 and index[0]!=-1:
            
            playedChamps.at[index[0], 'Wins'] = playedChamps.iloc[index[0]][1] + win
            playedChamps.at[index[0], 'Played'] = playedChamps.iloc[index[0]][2] + 1
        else:
            playedChamps = playedChamps.append({'Champion': champ,'Wins': win, 'Played': 1}, ignore_index=True)
        
        # print(playedChamps)


    playedChamps = playedChamps.sort_values(by=['Played'],ascending=False)
    print("Champion Pool :")
    print(playedChamps)

    



    printTreeMap(playedChamps)
    return len(regGames)



# @bot.command(name='scout')
# async def on_command(ctx):
#     print("command read")

@client.event 
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):

    cmd = message.content
    if message.author == client.user:
        return


    if cmd.startswith("scout "):
         
        global isRunning
        global chan
        ctx = message.channel
        pseudo = cmd[6:len(cmd)]

        if(isRunning):
            await ctx.send("A search is already running, please wait before trying again")
        else:
            isRunning = True
            await ctx.send('Searching Data for : "' + pseudo + '"')
            
            test = find(pseudo)
            if(test == 0):
                await ctx.send("This player wasn't in the database. The first load can take several minutes due to Riot API Key limitations")
            elif (test == 404):
                await ctx.send("Incorrect pseudo, player not found")
                isRunning = False
                return
            nbGame = scout(pseudo)
            
            await ctx.send(pseudo + ' Champion pool (' + str(nbGame) + ' games) : ')
            await ctx.send(file=discord.File('temp/discordPrint.png'))
            isRunning = False
 
            os.remove('temp/discordPrint.png')
            
    #await bot.process_commands(message)
         
async def sendMessage(message, chan):
    await chan.send(message)

client.run(token)
