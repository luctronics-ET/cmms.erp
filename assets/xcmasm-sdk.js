/**
 * xcmasm-sdk.js  —  SDK compartilhado do xCMASM
 * Uso: const sdk = xcmasm({ baseURL: 'http://localhost:8010' });
 * Todos os módulos HTML importam este arquivo para acessar o xCore.
 */
(function (global) {
  'use strict';

  const TOKEN_KEY = 'xcmasm_token';
  const USER_KEY  = 'xcmasm_user';

  function xcmasm(opts) {
    const baseURL = (opts && opts.baseURL) || 'http://localhost:8010';

    // ── HTTP helper ──────────────────────────────────────────────────────────
    async function _req(method, path, body, params) {
      const url = new URL(baseURL + path);
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined && v !== null) url.searchParams.set(k, v);
        });
      }
      const token = localStorage.getItem(TOKEN_KEY);
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = 'Bearer ' + token;

      try {
        const res = await fetch(url.toString(), {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw Object.assign(new Error(err.detail || res.statusText), { status: res.status });
        }
        return res.status === 204 ? null : res.json();
      } catch (e) {
        if (e.name === 'TypeError') {
          // xCore offline — retorna fallback silencioso
          console.warn('[xcmasm-sdk] xCore offline:', path);
          return null;
        }
        throw e;
      }
    }

    const get    = (path, params) => _req('GET',    path, null, params);
    const post   = (path, body)   => _req('POST',   path, body);
    const put    = (path, body)   => _req('PUT',    path, body);
    const patch  = (path, body)   => _req('PATCH',  path, body);

    // ── Auth ─────────────────────────────────────────────────────────────────
    const auth = {
      async login(mat, senha) {
        const data = await _req('POST', '/api/auth/login', { mat, senha });
        if (data) {
          localStorage.setItem(TOKEN_KEY, data.token);
          localStorage.setItem(USER_KEY, JSON.stringify(data.usuario));
        }
        return data;
      },

      async logout() {
        await _req('POST', '/api/auth/logout');
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      },

      isAuthenticated() {
        return !!localStorage.getItem(TOKEN_KEY);
      },

      me() {
        const raw = localStorage.getItem(USER_KEY);
        return raw ? JSON.parse(raw) : null;
      },

      async fetchMe() {
        return get('/api/auth/me');
      },
    };

    // ── Usuários ─────────────────────────────────────────────────────────────
    async function getUsuarios(filtros) {
      const data = await get('/api/usuarios', filtros);
      return data || [];
    }

    async function getUsuario(id) {
      return get('/api/usuarios/' + id);
    }

    async function criarUsuario(payload) {
      return post('/api/usuarios', payload);
    }

    async function atualizarUsuario(id, payload) {
      return put('/api/usuarios/' + id, payload);
    }

    // ── Estrutura / Organograma ───────────────────────────────────────────────
    async function getEstrutura() {
      const data = await get('/api/estrutura');
      return data || [];
    }

    async function getUnidades() {
      const data = await get('/api/unidades');
      return data || [];
    }

    // ── Ativos ────────────────────────────────────────────────────────────────
    async function getAtivos(categoria) {
      const data = await get('/api/ativos', categoria ? { categoria } : undefined);
      return data || [];
    }

    async function getAtivo(id) {
      return get('/api/ativos/' + id);
    }

    // ── Locais ────────────────────────────────────────────────────────────────
    async function getLocais(filtros) {
      const data = await get('/api/locais', filtros);
      return data || [];
    }

    async function getLocal(id) {
      return get('/api/locais/' + id);
    }

    async function criarLocal(payload) {
      return post('/api/locais', payload);
    }

    async function atualizarLocal(id, payload) {
      return put('/api/locais/' + id, payload);
    }

    // ── Ordens de Serviço ─────────────────────────────────────────────────────
    async function getOS(filtros) {
      const data = await get('/api/os', filtros);
      return data || [];
    }

    async function getOSDetalhe(id) {
      return get('/api/os/' + id);
    }

    async function criarOS(payload) {
      return post('/api/os', payload);
    }

    async function atualizarStatusOS(id, payload) {
      return put('/api/os/' + id + '/status', payload);
    }

    async function adicionarEtapaOS(osId, payload) {
      return post('/api/os/' + osId + '/etapas', payload);
    }

    async function toggleEtapaOS(osId, etapaId, concluida) {
      return patch('/api/os/' + osId + '/etapas/' + etapaId + '?concluida=' + (concluida ? 1 : 0));
    }

    async function getOSKpis(modulo) {
      const data = await get('/api/os/kpis', modulo ? { modulo } : undefined);
      return data || {};
    }

    // ── Estoque ───────────────────────────────────────────────────────────────
    async function getEstoque(filtros) {
      const data = await get('/api/estoque', filtros);
      return data || [];
    }

    async function getEstoqueItem(id) {
      return get('/api/estoque/' + id);
    }

    async function criarEstoqueItem(payload) {
      return post('/api/estoque', payload);
    }

    async function atualizarEstoqueItem(id, payload) {
      return put('/api/estoque/' + id, payload);
    }

    async function moverEstoque(id, movimento) {
      return post('/api/estoque/' + id + '/movimentos', movimento);
    }

    // ── Health ────────────────────────────────────────────────────────────────
    async function health() {
      return get('/api/health');
    }

    // ── Shared (compat localStorage) ─────────────────────────────────────────
    async function getShared() {
      return get('/api/shared');
    }

    return {
      auth,
      health,
      getShared,
      getUsuarios, getUsuario, criarUsuario, atualizarUsuario,
      getEstrutura, getUnidades,
      getAtivos, getAtivo,
      getLocais, getLocal, criarLocal, atualizarLocal,
      getOS, getOSDetalhe, criarOS, atualizarStatusOS, adicionarEtapaOS, toggleEtapaOS, getOSKpis,
      getEstoque, getEstoqueItem, criarEstoqueItem, atualizarEstoqueItem, moverEstoque,
    };
  }

  // Expose globally
  global.xcmasm = xcmasm;

})(typeof window !== 'undefined' ? window : this);
