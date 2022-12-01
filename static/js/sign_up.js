// Example starter JavaScript for disabling form submissions if there are invalid fields
(() => {
    'use strict'
  
    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    const forms = document.querySelectorAll('.needs-validation')
  
    // Loop over them and prevent submission
    Array.from(forms).forEach(form => {
      form.addEventListener('submit', event => {
        if (!form.checkValidity()) {
          event.preventDefault()
          event.stopPropagation()
        }
  
        form.classList.add('was-validated')
      }, false)
    })
  })()
  
  const check = document.getElementById('passcheck1')
  const check2 = document.getElementById('passcheck2')
  
  function clicked1() {
    if (check.type === 'password') {
      check.type = 'text';
      check2.type = 'text';
    }
    else {
      check.type = 'password';
      check2.type = 'password';
    }
  }  