# 🚀 High-Performance Sync & Upload TUI

🌍 Choose your language / Escolha seu idioma:
[🇺🇸 English](#english) | [🇧🇷 Português](#portuguese)

---

<h2 id="english">🇺🇸 English</h2>

### 📌 About the Project
This project is a high-performance, multithreaded Python automation tool designed to securely synchronize and upload large directories to a corporate SFTPGo server. Built specifically to handle high-latency I/O-bound operations, it maximizes available network bandwidth by multiplexing uploads across concurrent threads. 

A standout feature of this tool is its **Terminal User Interface (TUI)**, built with the `rich` library, which replaces standard terminal scrolling with a clean, static, real-time dashboard.

### ✨ Key Features
* **Maximized Bandwidth (Multithreading):** Uses `ThreadPoolExecutor` to run concurrent uploads, saturating high-speed connections while maintaining low CPU and RAM footprint.
* **Modern TUI Dashboard:** Features a static, flicker-free terminal dashboard with real-time progress bars, success/error counters, and live file status, preventing terminal output flooding.
* **Smart Synchronization:** Checks if a file already exists on the remote server before uploading, significantly saving time and bandwidth.
* **Advanced Session Management:** Implements Connection Pooling (`HTTPAdapter`), `Keep-Alive` tunnels, and dynamic CSRF token extraction.
* **Resilient Authentication:** Uses Thread Locks (`threading.Lock`) to safely refresh expired sessions and cookies without interrupting active background uploads.
* **Strict TLS/SSL Security:** Validates server identity using local `.crt`/`.pem` certificates, preventing Man-in-the-Middle (MITM) attacks.

### 🛠️ Technologies
* **Python 3.8+**
* `requests` & `urllib3` (Networking & Connection Pooling)
* `concurrent.futures` & `threading` (Concurrency & Locks)
* `beautifulsoup4` (HTML Parsing & CSRF handling)
* `rich` (Terminal UI & Live rendering)
* `python-dotenv` (Environment Variables)

### 🚀 How to Run
1. Clone the repository:

   git clone https://github.com/mateusfesilva/SFTPGo_files_uploader

2. Install dependencies:

   pip install -r requirements.txt

3. Set up Environment Variables:
   
   Copy the template file to create your local environment configuration:

   cp .env.example .env

   Open .env and fill in your target server URLs, local paths, and credentials.

4. Add the Server Certificate:
   
   Place the server's public certificate inside the cacert.pem file in the certifi lib directory.

6. Run the application:

   python main.py


<h2 id="portuguese">br Português</h2>

### 📌 Sobre o Projeto
Este projeto é uma ferramenta de automação em Python de alta performance e multithread, projetada para sincronizar e enviar grandes diretórios de forma segura para um servidor corporativo (SFTPGo). Construído para lidar com gargalos de rede (I/O-bound), ele maximiza a banda disponível multiplexando os envios através de threads simultâneas.

O grande diferencial desta ferramenta é a sua TUI (Interface de Usuário no Terminal), construída com a biblioteca rich, que substitui a rolagem infinita de texto por um painel de controle estático, limpo e em tempo real.

### ✨ Principais Funcionalidades
* **Banda Maximizada (Multithreading):** Utiliza ThreadPoolExecutor para uploads simultâneos, saturando conexões de alta velocidade mantendo o uso de CPU e RAM extremamente baixos.

* **Dashboard TUI Moderno:** Painel estático no terminal com barras de progresso, contadores de sucesso/erro e status de arquivos em tempo real, evitando a "inundação" de texto na tela.

* **Sincronização Inteligente:** Verifica se o arquivo já existe no servidor remoto antes de enviá-lo, poupando tempo e internet.

* **Gerenciamento Avançado de Sessão:** Implementa Connection Pooling (HTTPAdapter), túneis Keep-Alive e extração dinâmica de tokens CSRF.

* **Autenticação Resiliente:** Utiliza Cadeados de Thread (threading.Lock) para renovar sessões expiradas com segurança, sem derrubar as threads ativas.

* **Segurança TLS/SSL Rígida:** Valida a identidade do servidor usando certificados locais .crt/.pem, prevenindo ataques Man-in-the-Middle (MITM).

### 🛠️ Tecnologias
* **Python 3.8+**

* `requests & urllib3` (Rede e Connection Pooling)

* `concurrent.futures & threading` (Concorrência e Locks)

* `beautifulsoup4` (Extração de HTML e tokens CSRF)

* `rich` (Interface de terminal e Renderização Live)

* `python-dotenv` (Gerenciamento de Variáveis de Ambiente)

### 🚀 Como Executar
1. Clone o repositório:
   
   git clone https://github.com/mateusfesilva/SFTPGo_files_uploader

3. Instale as dependências:

   pip install -r requirements.txt

4. Configure as Variáveis de Ambiente:
   
   Copie o arquivo de modelo para criar sua configuração local:

   cp .env.example .env

   Abra o arquivo .env e preencha com as URLs do servidor alvo, caminhos locais e suas credenciais.

5. Adicione o Certificado do Servidor:
   
   Coloque o certificado público do servidor dentro do arquivo cacert.pem no diretório da biblioteca certifi.

7. Execute a aplicação:
   
   python main.py
