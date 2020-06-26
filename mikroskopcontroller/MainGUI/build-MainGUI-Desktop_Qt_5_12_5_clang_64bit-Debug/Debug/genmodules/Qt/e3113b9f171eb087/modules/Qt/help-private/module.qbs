import '../QtModule.qbs' as QtModule

QtModule {
    qtModuleName: "Help"
    Depends { name: "Qt"; submodules: ["core-private","help"]}

    architectures: []
    targetPlatform: "macos"
    hasLibrary: false
    staticLibsDebug: []
    staticLibsRelease: []
    dynamicLibsDebug: []
    dynamicLibsRelease: []
    linkerFlagsDebug: []
    linkerFlagsRelease: []
    frameworksDebug: []
    frameworksRelease: []
    frameworkPathsDebug: []
    frameworkPathsRelease: []
    libNameForLinkerDebug: undefined
    libNameForLinkerRelease: undefined
    libFilePathDebug: undefined
    libFilePathRelease: undefined
    pluginTypes: []
    moduleConfig: []
    cpp.defines: []
    cpp.includePaths: ["/Applications/Qt/5.12.5/clang_64/lib/QtHelp.framework/Headers/5.12.5","/Applications/Qt/5.12.5/clang_64/lib/QtHelp.framework/Headers/5.12.5/QtHelp"]
    cpp.libraryPaths: []
    
}
