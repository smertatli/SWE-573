const srcAssets = "src-assets";

module.exports = {
  "html": "html",
  "starter_kit": "starter-kit",
  "documentation": "documentation",
  "src_assets": "src-assets",
  "dist_assets": "dist-assets",
  "src_assets_path": "../../../assets",
  "dist_assets_path": "../../../app-assets",
  "destination": {
    "path": "dist-assets",
    "js": "dist-assets/js",
    "css": "dist-assets/css"
  },
  "source": {
    "path": srcAssets,
    "js": `${srcAssets}/js`,
    "jsEntry": `${srcAssets}/js/app/app.js`,
    "scss": `${srcAssets}/scss`,
    "html": "html"
  },
  "bundle": {
    "css": {
      "plugin": {
        "source": `${srcAssets}/scss/plugins`,
        "files": [
          "calendar/fullcalendar.min.css", 
          "pickadate/classic.css"
        ]
      }
    },
    "js": {
      "plugin": {
        "source": `${srcAssets}/js/plugins`,
        "files": [
          
        ]
      }
    }
  }
}