// stores/user.js
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const username = ref('')
  const email = ref('')
  const credits = ref('')
  // Other, to be configured later...

  return { username, email, credits }
})
