var stream = require('readable-stream')
var inherits = require('inherits')

var SIGNAL_FLUSH = Buffer.from([0])

var Bulk = function (opts, worker, flush) {
  if (!(this instanceof Bulk)) return new Bulk(opts, worker, flush)

  if (typeof opts === 'function') {
    flush = worker
    worker = opts
    opts = {}
  }

  stream.Writable.call(this, opts)
  this._worker = worker
  this._flush = flush
  this.destroyed = false
}

inherits(Bulk, stream.Writable)

Bulk.obj = function (opts, worker, flush) {
  if (typeof opts === 'function') return Bulk.obj(null, opts, worker)
  if (!opts) opts = {}
  opts.objectMode = true
  return new Bulk(opts, worker, flush)
}

Bulk.prototype.end = function (data, enc, cb) {
  if (!this._flush) return stream.Writable.prototype.end.apply(this, arguments)
  if (typeof data === 'function') return this.end(null, null, data)
  if (typeof enc === 'function') return this.end(data, null, enc)
  if (data) this.write(data)
  if (!this._writableState.ending) this.write(SIGNAL_FLUSH)
  return stream.Writable.prototype.end.call(this, cb)
}

Bulk.prototype.destroy = function (err) {
  if (this.destroyed) return
  this.destroyed = true
  if (err) this.emit('error', err)
  this.emit('close')
}

Bulk.prototype._write = function (data, enc, cb) {
  if (data === SIGNAL_FLUSH) this._flush(cb)
  else this._worker([data], cb)
}

Bulk.prototype._writev = function (batch, cb) {
  var len = batch.length
  if (batch[batch.length - 1].chunk === SIGNAL_FLUSH) {
    cb = this._flusher(cb)
    if (!--len) return cb()
  }
  var arr = new Array(len)
  for (var i = 0; i < len; i++) arr[i] = batch[i].chunk
  this._worker(arr, cb)
}

Bulk.prototype._flusher = function (cb) {
  var self = this
  return function (err) {
    if (err) return cb(err)
    self._flush(cb)
  }
}

module.exports = Bulk
