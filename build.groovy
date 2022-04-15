def build(mainRepoPath, boardDir = '.') {
    bat script: '''choco install -y git kicad imagemagick'''
    bat script: '''choco install -y python3 --version 3.9'''

    // Build a venv for some of our scripts. While some run in KiCad's Python runtime, some do not.
    bat script: '''\"c:\\Python39\\python.exe" -m venv venv'''

    // Checkout the main project, the one we will be building.
    mainCheckout = checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'RelativeTargetDirectory', relativeTargetDir: 'mainCheckout']], submoduleCfg: [], userRemoteConfigs: [[url: "${mainRepoPath}"]]])
    bat script: "copy mainCheckout\\${boardDir}\\* ."

    // Apply versioning according to git commit string
    buildNo = mainCheckout.GIT_COMMIT.substring(0, 5)
    bat script: "\"c:\\Program Files\\KiCad\\6.0\\bin\\python.exe\" versioning.py ${buildNo} ${BUILD_NUMBER}"

    // And export an image of the board.
    bat script: '''\"c:\\Program Files\\KiCad\\6.0\\bin\\python.exe\" export_SVG.py'''
    bat script: "refreshenv && magick mogrify -format png -trim -border 10 *.svg"
    archiveArtifacts artifacts: '*.png', caseSensitive: false, defaultExcludes: false

    // Now export gerbers..
    bat script: '''\"c:\\Program Files\\KiCad\\6.0\\bin\\python.exe\" export_gerber.py'''
    gerberFilename = "${JOB_NAME}_${BUILD_NUMBER}.zip"
    zip zipFile: gerberFilename, archive: false, dir: 'generated'
    archiveArtifacts gerberFilename
    bat label: '', returnStatus: true, script: "del ${gerberFilename}"

    // And run DRC, from our venv and not from KiCad's python runtime.
    def drcstatus = bat returnStatus: true, script: '''cmd /k \"venv\\Scripts\\activate.bat & python drc.py\"'''
    junit 'drc.xml'
    if (drcstatus != 0)
        error "DRC reported failure"
}

return this
