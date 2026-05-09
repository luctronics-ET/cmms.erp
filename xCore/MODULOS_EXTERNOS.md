# Módulos Externos

Primeira etapa da externalização: `Segurança`, `Paiol`, `CFTV` e `Calibração` passam a ser tratados pelo portal como módulos configuráveis por URL, sem depender de caminho físico dentro do repositório.

## Registro central

O arquivo [assets/xcmasm-module-links.js](../assets/xcmasm-module-links.js) concentra as URLs de navegação e de abertura dos módulos externos.

Campos:

- `navUrl`: URL usada pelo ERP no sidebar.
- `appUrl`: URL usada pelas páginas-ponte e launchers.
- `title`: tooltip institucional.

## Override sem editar código

É possível sobrescrever as URLs no navegador via `localStorage` com a chave `xcmasm_module_links`.

Exemplo:

```js
localStorage.setItem('xcmasm_module_links', JSON.stringify({
  seguranca: { navUrl: 'https://seguranca.cmasm.local', appUrl: 'https://seguranca.cmasm.local' },
  paiol: { navUrl: 'https://paiol.cmasm.local', appUrl: 'https://paiol.cmasm.local' },
  cftv: { navUrl: 'https://cftv.cmasm.local', appUrl: 'https://cftv.cmasm.local' },
  calibracao: { navUrl: 'https://calibracao.cmasm.local', appUrl: 'https://calibracao.cmasm.local' }
}));
```

Depois, recarregue o portal.

## Resultado esperado

- O ERP deixa de depender de links hardcoded espalhados.
- As páginas-ponte passam a abrir o destino configurado.
- A movimentação física das pastas pode ser feita depois, sem alterar o shell do `xCore`.