import zipfile, os, json
root = "."
out = "hx-lang.vsix"
if os.path.exists(out): os.remove(out)
include = [
    "package.json",
    "language-configuration.json",
    "README.md",
    "syntaxes/hx.tmLanguage.json",
    "snippets/hx.json",
    "python/hx.py",
    "python/hx_check.py",
    "out/extension.js",
    "out/providers.js",
    "out/runner.js",
    "out/diagnostics.js",
    "out/symbols.js",
    "out/agent/panel.js",
    "out/designer/panel.js",
]
ct = '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension=".json" ContentType="application/json"/><Default Extension=".js" ContentType="application/javascript"/><Default Extension=".py" ContentType="text/plain"/><Default Extension=".md" ContentType="text/markdown"/><Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>'
pkg = json.load(open(os.path.join(root, "package.json"), encoding="utf-8"))
manifest = '<?xml version="1.0" encoding="utf-8"?><PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" Id="%s" Version="%s" Publisher="%s"/><DisplayName>%s</DisplayName><Description xml:space="preserve">%s</Description><Categories>%s</Categories><Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="%s"/></Properties></Metadata><Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/><Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>' % (pkg["name"], pkg["version"], pkg["publisher"], pkg.get("displayName", pkg["name"]), pkg.get("description", ""), "|".join(pkg.get("categories", [])), pkg["engines"]["vscode"])
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct)
    z.writestr("extension.vsixmanifest", manifest)
    for rel in include:
        src = os.path.join(root, rel)
        if not os.path.exists(src):
            print("MISSING: " + rel)
            continue
        z.write(src, "extension/" + rel)
print("VSIX: " + out + " (" + str(os.path.getsize(out)) + " bytes)")