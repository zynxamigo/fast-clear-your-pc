# PC Cleaner Macro

Aplicativo de **limpeza segura do Windows** com **macros do sistema** (estilo Android MacroDroid). Remove lixo temporário sem tocar em pastas críticas como `System32`.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Windows](https://img.shields.io/badge/Windows-10%2F11-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## O que faz

### Limpeza Segura
- Remove arquivos temporários, cache de navegadores, lixeira, prefetch e mais
- **Nunca apaga** `System32`, `SysWOW64`, `Windows`, `Program Files` e pastas críticas
- Bloqueia exclusão de DLLs, drivers (`.sys`) e executáveis do sistema
- Mostra **quanto espaço foi liberado** após a limpeza

### Exclusões Personalizadas
- Proteja pastas, arquivos ou apps inteiros da limpeza
- Basta adicionar na aba **Exclusões** — eles nunca serão afetados

### Macros do Sistema (estilo Android)
Crie automações para:
- Executar comandos PowerShell/CMD
- Abrir aplicativos
- Criar pastas e arquivos
- Modificar o Registro do Windows
- Copiar/mover arquivos
- Criar atalhos
- Controlar serviços do Windows
- Exibir notificações
- E mais...

---

## Como baixar e instalar

### Opção 1 — Baixar do GitHub (recomendado)

1. Acesse o repositório:
   ```
   https://github.com/kelvi/pc-cleaner-macro
   ```

2. Clique no botão verde **Code** (Código)

3. Selecione **Download ZIP**

4. Extraia o ZIP em uma pasta, por exemplo:
   ```
   C:\Users\SeuUsuario\pc-cleaner-macro
   ```

5. Pronto! Não precisa instalar nada além do Python.

### Opção 2 — Clonar com Git

```bash
git clone https://github.com/kelvi/pc-cleaner-macro.git
cd pc-cleaner-macro
```

---

## Requisitos

- **Windows 10 ou 11**
- **Python 3.10 ou superior** — [Baixar Python](https://www.python.org/downloads/)

> Na instalação do Python, marque a opção **"Add Python to PATH"**.

---

## Como usar

### Iniciar o aplicativo

**Forma fácil:** dê duplo clique em `run.bat`

**Pelo terminal:**
```bash
cd pc-cleaner-macro
python main.py
```

### Fazer limpeza

1. Abra a aba **Limpeza**
2. Marque o que deseja limpar (ou deixe tudo marcado)
3. Clique em **Analisar espaço** para ver quanto pode liberar
4. Clique em **Limpar agora** para executar
5. Veja o relatório de **espaço liberado** na tela

### Proteger pastas/apps

1. Vá na aba **Exclusões**
2. Clique em **Adicionar pasta**, **Adicionar arquivo** ou **Adicionar app**
3. Selecione o que quer proteger
4. Esses itens nunca serão apagados na limpeza

### Criar macros

1. Vá na aba **Macros**
2. Clique em **Nova macro**
3. Dê um nome e escolha o gatilho (manual, ao iniciar, agendado)
4. Selecione uma ação (ex: `create_folder`, `open_app`, `run_command`)
5. Preencha os parâmetros e clique em **Adicionar ação**
6. Clique em **Salvar macro**
7. Selecione a macro e clique em **Executar**

---

## Proteções de segurança

O app **sempre protege** automaticamente:

| Protegido | Motivo |
|-----------|--------|
| `C:\Windows\System32` | Núcleo do Windows — **obrigatório** |
| `C:\Windows\SysWOW64` | Compatibilidade 32-bit |
| `C:\Windows` | Sistema operacional |
| `C:\Program Files` | Programas instalados |
| `.dll`, `.sys`, `.drv` | Bibliotecas e drivers |
| Itens na lista de exclusões | Escolha do usuário |

---

## Estrutura do projeto

```
pc-cleaner-macro/
├── main.py              # Inicia o app
├── run.bat              # Atalho para Windows
├── requirements.txt
├── README.md
├── data/                # Configurações salvas
│   ├── exclusions.json
│   └── macros.json
└── src/
    ├── cleaner/         # Motor de limpeza
    ├── macro/           # Motor de macros
    └── gui/             # Interface gráfica
```

---

## Licença

MIT — use livremente.

---

## Publicar no GitHub (para o desenvolvedor)

O projeto já está com Git inicializado. Para subir ao GitHub:

1. Crie um repositório novo em [github.com/new](https://github.com/new)
   - Nome: `pc-cleaner-macro`
   - Deixe **público**
   - **Não** marque "Add README" (já temos um)

2. No terminal, dentro da pasta do projeto:

```bash
cd C:\Users\kelvi\pc-cleaner-macro
git remote add origin https://github.com/SEU_USUARIO/pc-cleaner-macro.git
git branch -M main
git push -u origin main
```

3. Troque `SEU_USUARIO` pelo seu nome de usuário do GitHub.

Pronto — qualquer pessoa poderá baixar pelo botão **Code → Download ZIP**.

---

## Suporte

Encontrou um bug? Abra uma Issue no GitHub do repositório.