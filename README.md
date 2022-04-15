These files are for versioning KiCAD PCB designs in Jenkins.

Features:
* Recording the board version and git hash on your PCB (add text with the name 'GIT_XXXXX' and 'BUILD_XXX', it's just a simple text search-and-replace)
* Auto-run of DRC (unfortunately done via a load of really fragile UI scraping/scripting - improvements very much appreciated!)
* Generation of gerbers and an SVG image of the board

The idea is to prevent those 'oh no I forgot to DRC before I sent the board to the fab' moments.

Windows-only for now I'm afraid.

### Use

To use this, check it out in your Jenkinsfile and run the included groovy script. Something like this (excuse my crappy groovy):
```
node ("win10")
{
  checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'kicad-jenkins-support']], submoduleCfg: [], userRemoteConfigs: [[url: 'http://gitea/aliz/kicad-jenkins-support']]])
  bat script: 'copy kicad-jenkins-support\\* .'

  def rootDir = pwd()
  def kicadSupport = load "${rootDir}\\build.groovy"
  kicadSupport.build("path/to/your/project.git")
}
```