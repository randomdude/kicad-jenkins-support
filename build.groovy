def build(mainRepoPath, boardDir = '.') {
    bat script: '''choco install -y git python2 kicad imagemagick'''
    bat script: '''\"c:\\Python27\\python.exe" -m pip install pywinauto'''

    mainCheckout = checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'mainCheckout']], submoduleCfg: [], userRemoteConfigs: [[url: "${mainRepoPath}"]]])
    bat script: "copy mainCheckout\\${boardDir}\\* ."
    
    buildNo = mainCheckout.GIT_COMMIT.substring(0, 5)
    bat script: "\"c:\\Program Files\\KiCad\\6.0\\bin\\python.exe\" versioning.py ${buildNo} ${BUILD_NUMBER}"
    
    bat script: '''\"c:\\Program Files\\KiCad\\6.0\\bin\\python.exe\" export_SVG.py'''
    bat script: "refreshenv && magick mogrify -format png -trim -border 10 *.svg"
    archiveArtifacts artifacts: '*.png', caseSensitive: false, defaultExcludes: false

    bat script: '''\"c:\\Program Files\\KiCad\\6.0\\bin\\python.exe\" export_gerber.py'''
    gerberFilename = "${JOB_NAME}_${BUILD_NUMBER}.zip"
    zip zipFile: gerberFilename, archive: false, dir: 'generated'
    archiveArtifacts gerberFilename
    bat label: '', returnStatus: true, script: "del ${gerberFilename}"
 
    def drcstatus = bat returnStatus: true, script: '''\"c:\\python27\\python.exe\" drc.py'''
    junit 'drc.xml'
    if (drcstatus != 0)
        error "DRC reported failure"
}

return this
