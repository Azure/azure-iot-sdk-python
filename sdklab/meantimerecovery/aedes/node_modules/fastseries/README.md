# fastseries

![ci][ci-url]
[![npm version][npm-badge]][npm-url]
[![Coverage Status][coveralls-badge]][coveralls-url]
[![Dependency Status][david-badge]][david-url]

Zero-overhead series function call for node.js.
Also supports `each` and `map`!

If you need zero-overhead parallel function call, check out
[fastparallel](http://npm.im/fastparallel).

[![js-standard-style](https://raw.githubusercontent.com/feross/standard/master/badge.png)](https://github.com/feross/standard)

## Example for series call

```js
var series = require('fastseries')({
  // if you want the results, then here you are
  results: true
})

series(
  {}, // what will be this in the functions
  [something, something, something], // functions to call
  42, // the first argument of the functions
  done // the function to be called when the series ends
)

function late (arg, cb) {
  console.log('finishing', arg)
  cb(null, 'myresult-' + arg)
}

function something (arg, cb) {
  setTimeout(late, 1000, arg, cb)
}

function done (err, results) {
  console.log('series completed, results:', results)
}
```

## Example for each and map calls

```js
var series = require('fastseries')({
  // if you want the results, then here you are
  // passing false disables map
  results: true
})

series(
  {}, // what will be this in the functions
  something, // functions to call
  [1, 2, 3], // the first argument of the functions
  done // the function to be called when the series ends
)

function late (arg, cb) {
  console.log('finishing', arg)
  cb(null, 'myresult-' + arg)
}

function something (arg, cb) {
  setTimeout(late, 1000, arg, cb)
}

function done (err, results) {
  console.log('series completed, results:', results)
}
```

## Caveats

The `done` function will be called only once, even if more than one error happen.

This library works by caching the latest used function, so that running a new series
does not cause **any memory allocations**.

## Benchmarks

Benchmark for doing 3 calls `setImmediate` 1 million times:

```
benchSetImmediate*1000000: 2460.623ms
benchAsyncSeries*1000000: 3064.569ms
benchAsyncEachSeries*1000000: 2913.525ms
benchAsyncMapSeries*1000000: 3020.794ms
benchNeoSeries*1000000: 2617.064ms
benchNeoEachSeries*1000000: 2621.672ms
benchNeoMapSeries*1000000: 2611.294ms
benchTinyEachAsync*1000000: 2706.457ms
benchFastSeries*1000000: 2540.653ms
benchFastSeriesNoResults*1000000: 2538.674ms
benchFastSeriesEach*1000000: 2534.856ms
benchFastSeriesEachResults*1000000: 2545.394ms
```

Benchmarks taken on Node 12.16.1 on a dedicated server.

See [bench.js](./bench.js) for mode details.

## License

ISC

[ci-url]: https://github.com/mcollina/fastseries/workflows/ci/badge.svg
[npm-badge]: https://badge.fury.io/js/fastseries.svg
[npm-url]: https://badge.fury.io/js/fastseries
[coveralls-badge]:https://coveralls.io/repos/mcollina/fastseries/badge.svg?branch=master&service=github
[coveralls-url]: https://coveralls.io/github/mcollina/fastseries?branch=master
[david-badge]: https://david-dm.org/mcollina/fastseries.svg
[david-url]: https://david-dm.org/mcollina/fastseries
