# bulk-write-stream

Writable stream that forwards everything in the `highWaterMark` buffer
to a custom `write` function using the new [writev](https://nodejs.org/api/stream.html#stream_writable_writev_chunks_callback) api in streams

```
npm install bulk-write-stream
```

[![build status](http://img.shields.io/travis/mafintosh/bulk-write-stream.svg?style=flat)](http://travis-ci.org/mafintosh/bulk-write-stream)

## Usage

``` js
var bulk = require('bulk-write-stream')

var ws = bulk.obj(function (list, cb) {
  console.log('should write list of objects', list)
  cb()
})

ws.write('a')
ws.write('b')
ws.write('c')
ws.write('d')
```

## API

#### `var ws = bulk([options], write, [flush])`

Create a new binary bulk write stream. Options are forwarded to the writable stream constructor.
Write is called with `write(list, cb)` where list is everything currently buffered in the writable stream.

If you specify a flush function that will be called with `flush(cb)` before the stream emits `finish`.

#### `var ws = bulk.obj([options], write, [flush])`

A shorthand for setting `objectMode: true`

## License

MIT
