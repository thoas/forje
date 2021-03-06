import * as axios from 'axios'
import numeral from './format'

document.addEventListener('DOMContentLoaded', e => {
  const billingWrapper = document.querySelector('#billing-wrapper')
  const diff = document.querySelector('#id_diff')

  document.querySelector('#checkout-form').addEventListener('submit', e => {
    if (document.querySelector('#id_cgu').checked === false) {
      alert('Vous devez accepter les conditions générales de ventes.')
      e.preventDefault()
    }
  })

  diff.addEventListener('change', e => {
    if (e.target.checked) {
      billingWrapper.style.display = 'block'
    } else {
      billingWrapper.style.display = 'none'
    }
  })

  diff.dispatchEvent(new Event('change'))

  const addressTypeChange = (radios, typeInput) => {
    radios.forEach(radio =>
      radio.addEventListener('change', e => {
        if (radio.value == 1) {
          typeInput.style.display = 'none'
        } else {
          typeInput.style.display = 'block'
        }
      })
    )
  }

  addressTypeChange(
    document.querySelectorAll('input[name=shipping-address-type]'),
    document.querySelector('#id_shipping-address-business_name')
  )

  addressTypeChange(
    document.querySelectorAll('input[name=billing-address-type]'),
    document.querySelector('#id_billing-address-business_name')
  )

  document.querySelector('input[name=shipping-address-type]:checked').dispatchEvent(new Event('change'))
  document.querySelector('input[name=billing-address-type]:checked').dispatchEvent(new Event('change'))

  const totalContainer = document.querySelector('#total-container')

  axios.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded'
  axios.defaults.headers.post['X-Requested-With'] = 'XMLHttpRequest'

  document.querySelectorAll('.article-container p.delete a').forEach(elem =>
    elem.addEventListener('click', e => {
      e.preventDefault()

      const current = e.target
      const articleContainer = current.parentNode.parentNode

      var params = new URLSearchParams()
      params.append('action', current.getAttribute('data-action'))
      params.append('reference', current.getAttribute('data-reference'))

      axios.post(current.getAttribute('href'), params).then(res => {
        articleContainer.parentNode.removeChild(articleContainer)

        // amount are in cents
        const total = parseInt(res.data.total, 10) / 100.0

        totalContainer.textContent = numeral(total).format('0.00')
      })
    })
  )
})
