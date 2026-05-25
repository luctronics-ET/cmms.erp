import { createStore } from 'vuex'

export default createStore({
  state: {
    loading: false
  },
  mutations: {
    SET_LOADING(state, status) {
      state.loading = status
    }
  }
})
