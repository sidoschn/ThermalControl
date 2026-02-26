import subprocess
import time

def performAutoupdate():
    print("Running auto-update ( current version is: "" )") #somehow get a version indicator from the git repo
    #pullResult = os.system("git pull")
    pullResult = "cannot resolve git link"
    pullAttempt = 0
    while pullResult == "cannot resolve git link":
        print("attempt "+str(pullAttempt)+" to connect to github...")
        try:
            pullResult = subprocess.check_output("git pull", shell=True,text=True)
        except:
            print("cannot resolve git link")
            pullAttempt += 1
            time.sleep(1) # this delay is added in order to give the network time to setup
            if pullAttempt > 10:
                break

    if pullResult[0:7] == "Already":
        print("code is up to date!")
    elif pullResult[0:7] == "Updatin":
        print("")
        print("update recieved, exiting to apply changes...")
        print("")
        exit()
        
    else:
        print("autoupdate failure, no internet connection?")