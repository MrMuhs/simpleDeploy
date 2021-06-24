import os
import shutil
import time
import subprocess
import fnmatch

exePath = "C:\\Program Files\\TortoiseSVN\\bin\\svn.exe"
repoURL = "https://localhost:443/svn/myRepo"
svnIntegrationRepo = "svnRepoBot\\"
deployTargetFolder = "C:\\inetpub\\wwwroot\\"
loginUser = "--username deployTool"

# DONT USE THIS, just use the TortoiseSVN manual login once and afterwards the cache will do its job automatically!
#loginUser += ' --password <some password here> --no-auth-cache'

#################################
################################# functions to structure the deployment, this is the main part you want to edit
#################################

def preDeploy(commitMessages):
  print("::preDeploy()")

  output = subprocess.run(["iisreset", "/stop"], capture_output=True, shell=True)
  #print("::preDeploy() iisreset stop result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
  if output.returncode == 0:
    print("::preDeploy() iisreset stop ok")
    return {"result_pre" : True}
  else:
    print("::preDeploy() iisreset stop ERROR output=", output)
    return {"result_pre" : False}

def coreDeploySVN(commitMessages, preResult):
  print("::coreDeploySVN()")

  if preResult["result_pre"] == True:
    # first delete everything from the repo folder, so that deleted files are gone too
    for f in os.listdir(deployTargetFolder):
      if(os.path.isdir(os.path.join(deployTargetFolder, f))):
        shutil.rmtree(os.path.join(deployTargetFolder, f))
      else:
        os.remove(os.path.join(deployTargetFolder, f))

    # copy all, except the svn folder
    shutil.copytree(svnIntegrationRepo, deployTargetFolder, ignore = shutil.ignore_patterns(".svn"), dirs_exist_ok = True)
    preResult["result_core"] = True

    return preResult
  else:
    preResult["result_core"] = "skipped, pre error"
    return preResult

def postDeploy(commitMessages, preResult):
  print("::postDeploy()")

  if preResult["result_pre"] == True:
    output = subprocess.run(["iisreset", "/start"], capture_output=True, shell=True)
    #print("::postDeploy() iisreset start result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
    if output.returncode == 0:
      print("::preDeploy() iisreset start ok")
      preResult["result_post"] = True
      return preResult
    else:
      print("::preDeploy() iisreset start ERROR output=", output)
      preResult["result_post"] = False
      return preResult
  else:
    preResult["result_post"] = "skipped, pre error"
    return preResult

def executeDeploy(commitMessages):
  preResult = preDeploy(commitMessages)
  print("::executeDeploy() pre-deploy result:", preResult)
  preResult = coreDeploySVN(commitMessages, preResult)
  print("::executeDeploy() deploy result:", preResult)
  preResult = postDeploy(commitMessages, preResult)
  print("::executeDeploy() post-deploy result:", preResult)

#################################
################################# some tooling functions
#################################

def getRevisionLine(input):
  lines = str(input).split("\\r\\n")
  filtered = fnmatch.filter(lines, '*evision*')
  if len(filtered) >= 1:
    return filtered[0]
  else:
    return ""

def isRevisionHigher(base, checkIsHigher):
  if int((""+str(base)).replace("r", "")) < int((""+str(checkIsHigher)).replace("r", "")):
    return True
  return False

def checkoutRemote():
  if(os.path.isdir(svnIntegrationRepo) == False):
    print("::checkoutRemote() checkout the repo to '" + svnIntegrationRepo + "'")
    output = subprocess.run([exePath, "checkout", repoURL, svnIntegrationRepo]+loginUser.split(), capture_output=True)
    #print("::checkoutRemote() checkout result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
    if output.returncode == 0:
      print("::checkoutRemote() checkout ok:", getRevisionLine(output.stdout))
    else:
      print("::checkoutRemote() checkout ERROR output=", output)
  else:
    print("::checkoutRemote() directory exists, cant checkout")

def updateLocal():
  if(os.path.isdir(svnIntegrationRepo) == True):
    print("::updateLocal() repo is already their")
    output = subprocess.run([exePath, "info", svnIntegrationRepo]+loginUser.split(), capture_output=True)
    #print("::updateLocal() info result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
    if output.returncode == 0:
      output = subprocess.run([exePath, "update", svnIntegrationRepo]+loginUser.split(), capture_output=True)
      #print("::updateLocal() update result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
      if output.returncode == 0:
        print("::updateLocal() update ok:", getRevisionLine(output.stdout))
      else:
        print("::updateLocal() update ERROR output=", output)
    else:
      print("::updateLocal() info ERROR output=", output)
  else:
    print("::updateLocal() directory doesnt exist, cant update")

def getHighestRevision(input, skipFullHistory = False):
  outHighestRevObj = {}
  outHighestRevObj["rev"] = 0
  outHighestRevObj["time"] = 0
  outHighestRevObj["messageLines"] = []
  outHighestRevObj["full"] = []

  revs = str(input).split("------------------------------------------------------------------------")
  cntRevLines = 0
  for rev in revs:
    lines = list(filter(None, str(rev).split("\\r\\n"))) # remove empty lines by filtering
    if len(lines) >= 1:
      eleForFull = {}
      eleForFull["revData"] = lines[0].split(" | ")
      eleForFull["messageLines"] = []
      if len(eleForFull["revData"]) == 4:
        #print("::getHighestRevision() Line=", cntRevLines, "revData ->", eleForFull["revData"], "len(lines)=", len(lines), "Line 1:", lines[1])
        for k in range(1, len(lines)):
          eleForFull["messageLines"].append(lines[k])
        outHighestRevObj["full"].append(eleForFull)

        if cntRevLines == 0:
          outHighestRevObj["rev"] = eleForFull["revData"][0]
          outHighestRevObj["time"] = eleForFull["revData"][2]
          for k in range(1, len(lines)):
            outHighestRevObj["messageLines"].append(lines[k])

          if skipFullHistory == True:
            break

        cntRevLines = cntRevLines + 1

  return outHighestRevObj

#################################
################################# main program loop
#################################

while True:
  if(os.path.isdir(deployTargetFolder) == False):
    print("::main() deploy dir does not existing...")
    exit(-1)

  if(os.path.isdir(svnIntegrationRepo) == False):
    print("::main() local repo not existing, checking out...")
    checkoutRemote()
    # we just checked it out... we dont deploy here
  else:
    output = subprocess.run([exePath, "log", svnIntegrationRepo]+loginUser.split(), capture_output=True)
    #print("::main() log result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
    highestRevLocal = getHighestRevision(str(output.stdout), True)
    #print("::main() LOCAL", highestRevLocal)
    if output.returncode == 0:
      output = subprocess.run([exePath, "log", repoURL]+loginUser.split(), capture_output=True)
      #print("::main() log result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
      highestRevURL = getHighestRevision(str(output.stdout), True)
      #print("::main() URL", highestRevURL)
      if output.returncode == 0:
        #print("::main() local revision", highestRevLocal["rev"], "remote revision", highestRevURL["rev"])
        if isRevisionHigher(highestRevLocal["rev"], highestRevURL["rev"]):
          print("::main() we should deploy, local revision", highestRevLocal["rev"], "remote revision", highestRevURL["rev"])
          updateLocal()
          executeDeploy(highestRevURL["messageLines"])
        #else:
          #print("::main() nothing to do residentSleeper")
      else:
        print("::main() remote log ERROR output=", output)
    else:
      print("::main() local log ERROR output=", output)
  time.sleep(1)