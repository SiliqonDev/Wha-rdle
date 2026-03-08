import os, json
from modules import shared

startingData = {"currentGameData": {"gameId": -1, "answer": ""}, "stats": {}, "lastGameData": {}}

def getWordList():
    allowed_guesses = []
    possible_answers = []

    with open(f"{shared.path_to_bot}/files/allowed-guesses.txt", 'r') as f1:
        for line in f1:
            allowed_guesses.append(line.strip())
    with open(f"{shared.path_to_bot}/files/possible-answers.txt", 'r') as f2:
        for line in f2:
            possible_answers.append(line.strip())
    
    return allowed_guesses, possible_answers

def initDataFile():
    if os.path.exists(f"{shared.path_to_bot}/data.json"): return
    # make new file
    with open(f"{shared.path_to_bot}/data.json", 'w') as f:
        json.dump(startingData, f)
    
def getAllData():
    with open(f"{shared.path_to_bot}/data.json",'r') as f:
        return(json.load(f))

###
def getGameData():
    return getAllData()["currentGameData"]
def setGameData(newData):
    current = getAllData()
    current["currentGameData"] = newData
    with open(f"{shared.path_to_bot}/data.json", 'w') as f:
        json.dump(current, f)

###
def getLastGameData():
    data : dict = getAllData()
    return data['lastGameData']
def getLastGameDataOf(userId):
    data : dict = getAllData()
    if str(userId) in data["lastGameData"].keys():
        return data["lastGameData"][f"{userId}"]
    return {
        "id":-1,
        "guesses": [],
        "completed": False,
        "won": False,
        "answer": ""
    }
def setLastGameDataFor(userId, data):
    current = getAllData()
    current["lastGameData"][f"{userId}"] = data
    with open(f"{shared.path_to_bot}/data.json", "w") as f:
        json.dump(current, f)

###
def getAllPlayerStats():
    data = getAllData()
    return data["stats"]
def getPlayerStatsOf(userId):
    stats = getAllPlayerStats()
    # needs to be initialized?
    if str(userId) not in stats.keys():
        stats[f"{userId}"] = {
            "gamesPlayed": 0,
            "wins": 0,
        }
    return stats[f"{userId}"]
def setPlayerStatsFor(userId, stats):
    current = getAllData()
    current["stats"][f"{userId}"] = stats
    with open(f"{shared.path_to_bot}/data.json", "w") as f:
        json.dump(current, f)
def incrementPlayerStats(userId, increments : dict):
    stats = getPlayerStatsOf(userId)
    for k,v in increments.items():
        if k in stats.keys():
            stats[k] += v
        else:
            stats[k] = v
    setPlayerStatsFor(userId, stats)
