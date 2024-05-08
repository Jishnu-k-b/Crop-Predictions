const signUpButton = document.getElementById("signUp");
const signInButton = document.getElementById("signIn");
const container = document.getElementById("container");

const errorMessage = document.getElementById("register-error-message");
if (errorMessage) {
  container.classList.add("right-panel-active");
}
const errorMessageLogin = document.getElementById("login-error-message");
if (errorMessage) {
  container.classList.remove("right-panel-active");
}
signUpButton.addEventListener("click", () => {
  container.classList.add("right-panel-active");
});
signInButton.addEventListener("click", () => {
  container.classList.remove("right-panel-active");
});

setTimeout(function () {
  var errorMessage1 = document.getElementById("register-error-message");
  if (errorMessage1) {
    errorMessage1.style.display = "none";
  }
}, 5000); //
setTimeout(function () {
  var errorMessage2 = document.getElementById("login-error-message");
  if (errorMessage2) {
    errorMessage2.style.display = "none";
  }
}, 5000); //
