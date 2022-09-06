var parallel = require('./')({
  // this is a function that will be called
  // when a parallel completes
  released: completed,

  // we want results and errors
  // passing false will make it faster!
  results: true
})

parallel(
  {}, // what will be this in the functions
  [something, something, something], // functions to call
  42, // the first argument of the functions
  next // the function to be called when the parallel ends
)

function something (arg, cb) {
  setImmediate(cb, null, 'myresult')
}

function next (err, results) {
  if (err) {
    // do something here!
  }
  console.log('parallel completed, results:', results)

  parallel({}, something, [1, 2, 3], done)
}

function done (err, results) {
  if (err) {
    // do something here!
  }
  console.log('parallel completed, results:', results)
}

function completed () {
  console.log('parallel completed!')
}
