import os
import shutil
from datetime import datetime
import subprocess
import fnmatch

buildDate = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
newBuildFolder = os.path.join(os.getcwd(), "_build", buildDate)

exePath = "C:\\Program Files\\TortoiseSVN\\bin\\svn.exe"
repoURL = "https://localhost:443/svn/myRepo"
svnIntegrationRepo = "_build\\svnRepo\\"
loginUser = "--username deployTool"
commitMessage = "deploy "+buildDate

# DONT USE THIS, just use the TortoiseSVN manual login once and afterwards the cache will do its job automatically!
#loginUser += ' --password <some password here> --no-auth-cache'

#################################
################################# some tooling functions
#################################

def copyfolder(src, dst, symlinks=False, ignore=None, dirs_exist_ok=True):
  for item in os.listdir(src):
    s = os.path.join(src, item)
    d = os.path.join(dst, item)
    if os.path.isdir(s):
      shutil.copytree(s, d, symlinks=symlinks, ignore=ignore, dirs_exist_ok=dirs_exist_ok)
    else:
      shutil.copy2(s, d)

def getRevisionLine(input):
  lines = str(input).split("\\r\\n")
  filtered = fnmatch.filter(lines, '*evision*')
  if len(filtered) >= 1:
    return filtered[0]
  else:
    return ""

def getCommitNeeded():
  output = subprocess.run([exePath, "status", "-v", svnIntegrationRepo]+loginUser.split(), capture_output=True)
  #print("::deploy() status result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
  cntMod = 0
  cntDel = 0
  cntAdd = 0
  if output.returncode == 0:
    lines = str(output.stdout).split("\\r\\n")
    for line in lines:
      lineSplit = line.split()
      if len(lineSplit) == 5:
        if(lineSplit[0] == "M"):
          cntMod = cntMod + 1
        elif(lineSplit[0] == "D"):
          cntDel = cntDel + 1
        elif(lineSplit[0] == "A"):
          cntAdd = cntAdd + 1
    if cntMod > 0 or cntDel > 0 or cntAdd > 0:
      print("::getCommitNeeded() add",cntAdd,"changed",cntMod,"deleted",cntDel)
      return True
    else:
      return False
  else:
    print("::printCommitStats() status ERROR output=", output)
    return True

#################################
################################# main program
#################################

# This would be a place to extend build procedure, by e.g. compiler calles etc., i my case, i just copy files:
# -->
shutil.copytree(".", newBuildFolder, ignore = shutil.ignore_patterns("_notes.md", "_deploy.py", "_deployBot.py", "_build", "prototypeImage.php"))
# <--

if(os.path.isdir(svnIntegrationRepo)):
  print("::deploy() repo is already their")
  output = subprocess.run([exePath, "info", svnIntegrationRepo], capture_output=True)
  #print("::deploy() info result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
  if output.returncode == 0:
    print("::deploy() info ok:", getRevisionLine(output.stdout))
    output = subprocess.run([exePath, "update", svnIntegrationRepo]+loginUser.split(), capture_output=True)
    #print("::deploy() update result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
    if output.returncode == 0:
      print("::deploy() update ok:", getRevisionLine(output.stdout))
    else:
      print("::deploy() update ERROR output=", output)
  else:
    print("::deploy() info ERROR output=", output)
else:
  print("::deploy() checkout the repo to '" + svnIntegrationRepo + "'")
  output = subprocess.run([exePath, "checkout", repoURL, svnIntegrationRepo]+loginUser.split(), capture_output=True)
  #print("::deploy() checkout result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
  if output.returncode == 0:
    print("::deploy() checkout ok:", getRevisionLine(output.stdout))
  else:
    print("::deploy() checkout ERROR output=", output)

# New we merge the stuff from "build" folder to the local repo. For this we just clean the folder and move the new in.
# First delete everything from the repo folder, so that deleted files are gone too.
for f in os.listdir(svnIntegrationRepo):
  if f == ".svn":
    continue
  if(os.path.isdir(os.path.join(svnIntegrationRepo, f))):
    shutil.rmtree(os.path.join(svnIntegrationRepo, f))
  else:
    os.remove(os.path.join(svnIntegrationRepo, f))

# Copy the build folder stuff to the local repo
copyfolder(newBuildFolder, svnIntegrationRepo)

# Obviously, the merge could be avoid here by directly copy to the repo, as my example here just copies simple files.
# This script stands as a template, to use it for more complex build steps

# Add deleted files to the commit
# [PM] maybe their is a better way of just using svn command line to add "deleted" files to the commit... but didnt find it
# For now, find deleted files by status output and use "svn delete" on them:
output = subprocess.run([exePath, "status", "-v", svnIntegrationRepo]+loginUser.split(), capture_output=True)
#print("::deploy() status result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
if output.returncode == 0:
  print("::deploy() status ok")
  lines = str(output.stdout).split("\\r\\n")
  for line in lines:
    lineSplit = line.split()
    if len(lineSplit) == 5:
      if(lineSplit[0] == "!"):
        output = subprocess.run([exePath, "delete", "--force", lineSplit[4]]+loginUser.split(), capture_output=True)
        #print("::deploy() delete result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
        if output.returncode == 0:
          print("::deploy() delete ok:", lineSplit[4])
        else:
          print("::deploy() delete ERROR output=", output)
else:
  print("::deploy() status ERROR output=", output)

# Add new add files to the commit
output = subprocess.run([exePath, "add", "--force", "--auto-props", "--parents", "--depth", "infinity", svnIntegrationRepo]+loginUser.split(), capture_output=True)
#print("::deploy() add result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
if output.returncode == 0:
  print("::deploy() add ok")
  if getCommitNeeded() == True:
    output = subprocess.run([exePath, "commit", "-m", commitMessage, svnIntegrationRepo]+loginUser.split(), capture_output=True)
    #print("::deploy() commit result: returncode='"+str(output.returncode)+"' stdout='"+str(output.stdout).replace("\\r\\n", "\n")+"'")
    if output.returncode == 0:
      print("::deploy() commit ok:", getRevisionLine(output.stdout))
    else:
      print("::deploy() commit ERROR output=", output)
  else:
    print("::deploy() nothing to commit")
else:
  print("::deploy() add ERROR output=", output)