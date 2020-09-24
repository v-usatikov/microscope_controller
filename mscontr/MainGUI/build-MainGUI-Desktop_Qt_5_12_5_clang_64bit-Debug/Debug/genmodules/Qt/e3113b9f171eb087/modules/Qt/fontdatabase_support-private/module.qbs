import '../QtModule.qbs' as QtModule

QtModule {
    qtModuleName: "FontDatabaseSupport"
    Depends { name: "Qt"; submodules: ["core-private","gui-private"]}

    architectures: ["x86_64"]
    targetPlatform: "macos"
    hasLibrary: true
    staticLibsDebug: ["/Applications/Qt/5.12.5/clang_64/lib/libqtfreetype_debug.a","z","/Applications/Qt/5.12.5/clang_64/lib/libqtlibpng_debug.a"]
    staticLibsRelease: ["/Applications/Qt/5.12.5/clang_64/lib/libqtfreetype.a","z","/Applications/Qt/5.12.5/clang_64/lib/libqtlibpng.a"]
    dynamicLibsDebug: []
    dynamicLibsRelease: []
    linkerFlagsDebug: []
    linkerFlagsRelease: []
    frameworksDebug: ["QtGui","QtCore","DiskArbitration","IOKit","CoreFoundation","CoreGraphics","CoreText","Foundation","AppKit","OpenGL","AGL"]
    frameworksRelease: ["QtGui","QtCore","DiskArbitration","IOKit","CoreFoundation","CoreGraphics","CoreText","Foundation","AppKit","OpenGL","AGL"]
    frameworkPathsDebug: ["/Applications/Qt/5.12.5/clang_64/lib"]
    frameworkPathsRelease: ["/Applications/Qt/5.12.5/clang_64/lib"]
    libNameForLinkerDebug: "Qt5FontDatabaseSupport_debug"
    libNameForLinkerRelease: "Qt5FontDatabaseSupport"
    libFilePathDebug: "/Applications/Qt/5.12.5/clang_64/lib/libQt5FontDatabaseSupport_debug.a"
    libFilePathRelease: "/Applications/Qt/5.12.5/clang_64/lib/libQt5FontDatabaseSupport.a"
    pluginTypes: []
    moduleConfig: ["lex","yacc","depend_includepath","testcase_targets","import_qpa_plugin","asset_catalogs","rez","qt_build_extra","file_copies","qmake_use","qt","warn_on","release","link_prl","app_bundle","incremental","global_init_link_order","lib_version_first","sdk","clang_pch_style","qt_framework","release","macos","osx","macx","mac","darwin","unix","posix","gcc","clang","llvm","sse2","aesni","sse3","ssse3","sse4_1","sse4_2","avx","avx2","avx512f","avx512bw","avx512cd","avx512dq","avx512er","avx512ifma","avx512pf","avx512vbmi","avx512vl","compile_examples","f16c","largefile","precompile_header","rdrnd","shani","x86SimdAlways","prefix_build","force_independent","utf8_source","create_prl","link_prl","prepare_docs","qt_docs_targets","no_private_qt_headers_warning","QTDIR_build","qt_example_installs","exceptions_off","testcase_exceptions","explicitlib","testcase_no_bundle","warning_clean","release","ReleaseBuild","Release","build_pass","static","internal_module","watchos_coretext","relative_qt_rpath","app_extension_api_only","git_build","qmake_cache","target_qt","c++11","strict_c++","c++14","c99","c11","hide_symbols","separate_debug_info","qt_install_headers","need_fwd_pri","qt_install_module","debug_and_release","build_all","compiler_supports_fpmath","create_libtool","release","ReleaseBuild","Release","build_pass","have_target","staticlib","exclusive_builds","objective_c","no_autoqmake","thread","opengl","moc","resources"]
    cpp.defines: ["QT_FONTDATABASE_SUPPORT_LIB"]
    cpp.includePaths: ["/Applications/Qt/5.12.5/clang_64/include","/Applications/Qt/5.12.5/clang_64/include/QtFontDatabaseSupport","/Applications/Qt/5.12.5/clang_64/include/QtFontDatabaseSupport/5.12.5","/Applications/Qt/5.12.5/clang_64/include/QtFontDatabaseSupport/5.12.5/QtFontDatabaseSupport"]
    cpp.libraryPaths: []
    isStaticLibrary: true
Group {
        files: [Qt["fontdatabase_support-private"].libFilePath]
        filesAreTargets: true
        fileTags: ["staticlibrary"]
    }
}
