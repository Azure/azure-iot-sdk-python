/*jslint node: true */
"use strict";

module.exports = function (grunt)
{
    grunt.initConfig(
    {
        jshint: {
            all: [ 'Gruntfile.js', 'index.js', 'lib/*.js', 'aedes/**/*.js', 'test/*.js', 'bench/**/*.js' ],
            options: {
                esversion: 9,
                node: true
            }
        },

        mochaTest: {
            src: 'test/*.js'
        },

        apidox: {
            input: 'lib/qlobber.js',
            output: 'README.md',
            fullSourceDescription: true,
            extraHeadingLevels: 1
        },

        exec: {
            cover: {
                cmd: "./node_modules/.bin/nyc -x Gruntfile.js -x 'test/**' node --expose-gc ./node_modules/.bin/grunt test"
            },

            cover_report: {
                cmd: './node_modules/.bin/nyc report -r lcov'
            },

            cover_check: {
                cmd: './node_modules/.bin/nyc check-coverage --statements 100 --branches 100 --functions 100 --lines 100'
            },

            coveralls: {
                cmd: 'cat coverage/lcov.info | coveralls'
            },

            bench: {
                cmd: './node_modules/.bin/bench -c 20000 -i bench/options/default.js,bench/options/dedup.js,bench/options/mapval.js,bench/options/default-native.js,bench/options/dedup-native.js,bench/options/default-cache-splits.js -k options bench/add bench/add_match_remove bench/match bench/match_search bench/test'
            },

            'bench-check': {
                cmd: './node_modules/.bin/bench -c 20000 -i bench/options/check-default.js,bench/options/check-dedup.js,bench/options/check-mapval.js,bench/options/check-default-native.js,bench/options/check-dedup-native.js -k options bench/add bench/add_match_remove bench/match bench/match_search bench/test'
            },

            'bench-many': {
                cmd: './node_modules/.bin/bench -c 1 -i bench/options/default.js,bench/options/dedup.js,bench/options/mapval.js,bench/options/default-native.js,bench/options/dedup-native.js,bench/options/default-cache-splits.js -k options bench/add_many bench/add_shortcut_many bench/match_many bench/match_search_many bench/test_many'
            }
        }
    });
    
    grunt.loadNpmTasks('grunt-contrib-jshint');
    grunt.loadNpmTasks('grunt-mocha-test');
    grunt.loadNpmTasks('grunt-apidox');
    grunt.loadNpmTasks('grunt-exec');

    grunt.registerTask('lint', 'jshint');
    grunt.registerTask('test', 'mochaTest');
    grunt.registerTask('docs', 'apidox');
    grunt.registerTask('coverage', ['exec:cover',
                                    'exec:cover_report',
                                    'exec:cover_check']);
    grunt.registerTask('coveralls', 'exec:coveralls');
    grunt.registerTask('bench', ['exec:bench',
                                 'exec:bench-many']);
    grunt.registerTask('bench-check', 'exec:bench-check');
    grunt.registerTask('default', ['lint', 'test']);
};
