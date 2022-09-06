var series = require('./')({
  // this is a function that will be called
  // when a series completes
  released: completed,

  // we want results and errors
  // passing false will make it faster!
  results: true
})

series(
  {}, // what will be this in the functions
  [something, something, something], // functions to call
  42, // the first argument of the functions
  next // the function to be called when the series ends
)

function late (arg, cb) {
  console.log('finishing', arg)
  cb(null, 'myresult-' + arg)
}

function something (arg, cb) {
  setTimeout(late, 1000, arg, cb)
}

function next (err, results) {
  if (err) {
    // do something here!
  }
  console.log('series completed, results:', results)

  series({}, something, [1, 2, 3], done)
}

function done (err, results) {
  if (err) {
    // do something here!
  }
  console.log('series completed, results:', results)
}

function completed () {
  console.log('series completed!')
}
