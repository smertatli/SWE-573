var gulp = require("gulp");
var gutil = require("gulp-util");
var minimist = require("minimist");
var config = require("./gulp.config");

var options = minimist(process.argv.slice(2));

global.config = config;
global.buildOptions = options;

gutil.log(gutil.colors.green("Starting Gulp Tasks!!"));

const envTasks = require("./gulp/environment")(gulp);
const cleanTasks = require("./gulp/clean")(gulp);
const scssTasks = require("./gulp/scss")(gulp);
const cssTasks = require("./gulp/css")(gulp);
const minifyTasks = require("./gulp/minify")(gulp);
const jsTasks = require("./gulp/javascript")(gulp);
const htmlTasks = require("./gulp/html")(gulp);
const staticAssetTasks = require("./gulp/static-asset")(gulp);
const uglifyTasks = require("./gulp/uglify")(gulp);
const serve = require("./gulp/serve")(gulp);
const pugTasks = require("./gulp/pug")(gulp);

// Compile SASS
gulp.task("compile-sass", gulp.parallel(scssTasks.compile));

// Bundle plugin css
gulp.task("bundle-plugin-css", gulp.parallel(cssTasks.pluginConcat));

// Compile Js
gulp.task("compile-js", gulp.parallel(jsTasks.compile));

// Generates CSS Distribution files.
gulp.task(
  "build-css",
  gulp.series(
    cleanTasks.css,
    scssTasks.compile,
    cssTasks.pluginCopy,
    minifyTasks.css,
    cssTasks.pluginConcat
  )
);

// Generates Js Distribution files.
gulp.task(
  "build-js",
  gulp.series(
    cleanTasks.js,
    jsTasks.appBundle,
    jsTasks.copy,
    jsTasks.compile,
    uglifyTasks.js
  )
);

// Starts local server
gulp.task(
  "serve",
  gulp.series(
    envTasks.setDev,
    "build-css",
    "build-js",
    staticAssetTasks.copy,
    serve.init,
    gulp.parallel(
      scssTasks.watch,
      jsTasks.watch,
      htmlTasks.watch,
      staticAssetTasks.watch
    )
  )
);

gulp.task(
  "build",
  gulp.series(
    envTasks.setProd,
    "build-css",
    "build-js",
    staticAssetTasks.copy
  )
);



// option --layout required
gulp.task("pug", gulp.series(pugTasks.buildTemplates, pugTasks.compile));

gulp.task("compile-pug", gulp.parallel(pugTasks.compile));

// option --layout required
gulp.task(
  "serve-pug",
  gulp.series(
    envTasks.setDev,
    pugTasks.buildTemplates,
    pugTasks.compile,
    "build-css",
    "build-js",
    staticAssetTasks.copy,
    serve.init,
    gulp.parallel(
      scssTasks.watch,
      jsTasks.watch,
      pugTasks.watch,
      staticAssetTasks.watch
    )
  )
);

gulp.task(
  "build-pug",
  gulp.series(
    envTasks.setProd,
    pugTasks.buildTemplates,
    pugTasks.compile,
    "build-css",
    "build-js",
    staticAssetTasks.copy
  )
);

gulp.task("default", gulp.parallel("serve"));
