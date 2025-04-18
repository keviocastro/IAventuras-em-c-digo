<h1>Sistema de Gerenciamento de academia</h1>

<p>Este projeto consiste em uma aplicação web desenvolvida em Flask, utilizando RabbitMQ para gerenciar filas de check-ins em massa e PostgreSQL para armazenar os dados</p>

<h2>Tecnologias Utilizadas</h2>
<ul>
  <li><strong>Flask</strong>: Framework web para a criação da API e frontend</li>
  <li><strong>RabbitMQ</strong>: Mensageria para gerenciar filas de check-in em massa</li>
  <li><strong>PostgreSQL</strong>: Banco de dados relacional para armazenamento de dados</li>
  <li><strong>Scikit-learn</strong>: Biblioteca utilizada para o treinamento do modelo de previsão de risco de churn</li>
  <li><strong>Docker</strong>: Usado para facilitar a configuração do ambiente de desenvolvimento e deploy</li>
</ul>

<h2>Como Rodar o Projeto</h2>

<h3>Requisitos</h3>
<p>Certifique-se de ter o Docker instalado em sua máquina.</p>

<h3>Passo a Passo para Deploy</h3>
<ol>
  <li>Clone o repositório para sua máquina local:
    <pre><code>git clone https://github.com/rafaelsorgato/IAventuras-em-c-digo.git</code></pre>
  </li>
  <li>Navegue até a pasta do projeto:
    <pre><code>cd IAventuras-em-c-digo</code></pre>
  </li>
  <li>Execute o comando para criar e rodar os containers com o Docker Compose:
    <pre><code>docker-compose up --build</code></pre>
    Este comando irá:
    <ul>
      <li>Construir a imagem do projeto.</li>
      <li>Subir os containers necessários: Flask, RabbitMQ, PostgreSQL.</li>
      <li>A aplicação estará disponível em <strong>http://localhost:5000</strong>.</li>
    </ul>
  </li>
</ol>

<h2>Documentação da API (Swagger)</h2>
<p>A documentação da API foi criada com Swagger. Você pode visualizar a documentação e interagir com a API através do seguinte link:</p>
<ul>
  <li><a href="https://app.swaggerhub.com/apis/RafaelSorgato/Aventuras/1.0" target="_blank">Documentação da API Swagger</a></li>
</ul>

<h2>Modelo de Previsão (Risco de Churn)</h2>
<p>O modelo de risco de churn foi treinado utilizando a biblioteca <strong>scikit-learn</strong>. O processo de treinamento foi feito com dados gerados artificialmente para simular um cenário próximo ao real. Esses dados incluem ruídos para tornar a previsão mais robusta.</p>

<h2>Arquivos Relacionados ao Treinamento do Modelo</h2>
<ul>
  <li><strong>`treinamento_detalhes.ipynb`</strong>: Análise e treinamento do modelo com detalhamento das etapas.</li>
  <li><strong>`treinamento.py`</strong>: Script focado exclusivamente no treinamento do modelo de previsão de risco de churn.</li>
</ul>

<h2>Sobre os Dados de Treinamento</h2>
<p>Os dados utilizados para treinar o modelo foram gerados manualmente, com a intenção de simular um cenário real, contendo tanto dados bons quanto com ruídos. Devido a essa geração personalizada, não será necessário realizar correções ou formatações adicionais.</p>

<h2>Contato</h2>
<ul>
  <li><strong>Autor</strong>: Rafael Sorgato</li>
  <li><strong>E-mail</strong>: rafaelsorgato@hotmail.com</li>
  <li><strong>Celular</strong>: 61 983633075</li>
</ul>
