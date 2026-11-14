# VESTE 2 — seu guarda-roupa inteligente

Aplicativo web instalável (PWA), em português, para organizar fotos de roupas reais e criar looks adequados ao seu estilo e à ocasião. **A versão 2 mantém a mesma base local e as mesmas chaves de armazenamento da versão 1**, de modo que a atualização no mesmo endereço normalmente preserva as peças, favoritos e histórico.

## Novidades da versão 2

1. **Reconhecimento visual opcional com IA.** Depois de conectar sua chave pessoal do Google Gemini em **Meu estilo → Conectar IA**, fotografe uma peça. A IA pode sugerir nome, categoria, cor, estampa, modelagem, nível de formalidade, ocasiões, temperatura e estilos. **Revise e corrija tudo antes de salvar.**
2. **O que vestir hoje?** Na tela Início, informe a cidade e clique em **Ver previsão**. O VESTE consulta o serviço Open-Meteo e usa temperatura e chance de chuva para sugerir roupas do seu closet. Sem internet, o clima permanece manual.
3. **Minha semana.** Uma nova aba gera looks para sete dias, com ocasião de segunda a sexta e outra para sábado e domingo. Tenta variar os itens e usa a previsão, se consultada.
4. **Peças esquecidas.** O closet destaca as roupas com menos usos registrados.
5. **Regras de preferência.** Permite evitar combinações de duas cores, controlar o uso de acessórios e evitar repetir peças recentemente.
6. **Consultoria opcional de IA para looks.** Depois de gerar combinações, o botão **Analisar looks com IA** envia **descrições cadastradas das peças, não as fotos**, para receber uma segunda avaliação e reordenação.
7. **Backup compatível.** Exportação e restauração em JSON continuam funcionando com arquivos da versão 1.

## Instalar pela primeira vez

1. Descompacte `VESTE_v2.zip`.
2. Em <https://app.netlify.com/drop>, publique os arquivos do app (enviando a pasta extraída como site).
3. Abra o endereço HTTPS no Safari do iPhone.
4. Se desejar, use **Compartilhar → Adicionar à Tela de Início**.

## Atualizar uma instalação da versão 1 sem perder seu closet

1. Abra a **versão 1 no endereço que você usa hoje** e entre em **Meu estilo → Exportar backup**. Guarde o JSON em Arquivos ou iCloud Drive.
2. Acesse o painel do **mesmo site** no Netlify, vá à área de deploys e envie a pasta com a versão 2 para esse site existente. **Não crie um segundo endereço**, pois o armazenamento local é separado por origem/endereço.
3. Abra novamente o endereço original no Safari. Pode ser necessário fechar o app e atualizar a página para que o novo service worker assuma.
4. Confira o closet, favoritos e histórico. Se estiverem vazios, use **Restaurar backup** do arquivo JSON exportado.

Observação: baixar um ZIP por si só não publica nem instala o aplicativo. Ao trocar de iPhone ou limpar dados do Safari, use um backup. Fotos e registros **não são sincronizados entre dispositivos**.

## Como conectar IA

1. Obtenha uma chave pessoal em <https://aistudio.google.com/apikey> (requer conta Google e acesso à API).
2. Em **Meu estilo → Conectar IA**, cole a chave e deixe o modelo padrão `gemini-3.6-flash` ou digite um modelo que esteja habilitado na sua conta.
3. Clique **Conectar nesta sessão**. O aplicativo **não guarda sua chave** em `localStorage`, `IndexedDB` ou backups. Você precisará inseri-la de novo quando recarregar.
4. Ao adicionar uma foto, use **Identificar peça com IA** ou mantenha ligada a opção de analisar automaticamente. Confira os campos antes de salvar.
5. Em **Criar looks**, o botão **Analisar looks com IA** pede uma nova avaliação a partir de metadados de até cinco combinações.

**Privacidade e custos:** suas fotos de roupas permanecem no navegador, **exceto quando você chama a classificação com IA, situação em que a foto é enviada ao Google**. As descrições das peças são enviadas quando você usa análise de looks com IA. A consulta do clima envia a cidade aos serviços Open-Meteo. Serviços externos podem exigir rede, ter limites de uso e cobrar por requisições. Não compartilhe a chave de API; não a insira em um projeto público nem em arquivos que serão compartilhados.

## Como obter boas sugestões

- Cadastre pelo menos partes de cima, partes de baixo e calçados. Uma peça única, como vestido, também funciona como base.
- Fotografe cada item individualmente, com boa luz e fundo simples.
- Marque suas preferências em **Meu estilo** e escolha as ocasiões e temperaturas adequadas de cada roupa.
- Use **Amei** e **Não usaria**, salve seus favoritos e clique em **Usei esse look** quando realmente vestir a combinação.
- As regras de não repetição são **preferências**, não garantias absolutas: com poucas peças pode ser inevitável repetir alguma roupa, especialmente calçados.

## Limitações atuais

- A primeira avaliação dos looks é feita por regras de compatibilidade, histórico de uso e preferências. A revisão textual por IA é opcional.
- O app não simula roupas sobre uma foto de uma pessoa; exibe colagens das fotos cadastradas.
- Sem chave de IA, a classificação de categoria, estampa e modelagem é manual; somente há uma sugestão aproximada da cor por processamento local.
- A previsão pode falhar sem internet, por limitação do serviço ou geocodificação imprecisa; selecione manualmente um clima nesse caso.
- **Não há login, backend, sincronização na nuvem nem acesso multiusuário.** O uso do mesmo endereço no mesmo navegador e o backup continuam essenciais.
- A chave pessoal em um aplicativo 100% frontend é adequada para testes particulares, mas não para distribuição pública com uma chave compartilhada. Para um produto lançado a outras pessoas, será necessário um backend protegido e autenticação.

## Desenvolvimento local

```bash
python3 -m http.server 8080
```

Abra `http://localhost:8080`. Todos os arquivos do app precisam ficar na mesma pasta: `index.html`, `app.js`, `styles.css`, `extra.css`, `sw.js`, `manifest.webmanifest` e os ícones.

## VESTE 3.0 — Ateliê

- Motor local com peças fixadas, troca individual, variedade de looks, feedback por motivo e preferências de silhueta/cobertura/cartela.
- Cadastro em lote (fila de até 50 fotos para revisar individualmente), sugestão de detalhes por IA, alerta de foto idêntica, recorte local aproximado de fundos uniformes e preço opcional.
- Ateliê: teste visual com ilustrações, consultora local por palavras-chave ou Gemini, calendário de uso, custo por uso, disponibilidade/lavanderia, compras em avaliação e checklist de mala.
- Provador com foto selecionada na sessão e Gemini de imagem opcional (modelo configurável). A simulação não mede tamanho nem garante caimento. Consultoria por foto, orientação de cores e provador exigem chave e confirmação de envio ao Google; podem gerar custos. Nenhuma chave vai ao repositório. A conversa e fotos pessoais do ateliê ficam apenas na memória da sessão.
- Login, sincronização e nuvem continuam fora desta versão. Faça backup antes de atualizar. O motor usa uma busca limitada e heurística; não garante a melhor combinação global.

### Importar peças sem substituir o closet

Na aba Closet, escolha **Importar peças (.json)**. Aceita um pacote `veste-pieces` ou um backup VESTE. Somente peças novas são adicionadas; não importa configurações nem histórico e ignora ID, foto ou nome/categoria/cor duplicados. Nenhuma foto pessoal está incluída no repositório. As peças importadas ficam no IndexedDB local.

### Closet ilustrado para teste (3.2)

Na primeira abertura com closet vazio, seis roupas de demonstração são geradas localmente como PNGs de ilustrações genéricas, sem fotos pessoais no repositório. Os registros têm marcação de teste e podem ser removidos em Meu closet. Nunca substitui um closet existente. Se o usuário trocar a imagem de uma peça ilustrada, ela passa a ser considerada uma peça real. A importação de fotos reais continua disponível. Os dados são privados no navegador e não há sincronização.

## VESTE 4.0 — login e sincronização

Projeto Supabase Veste conectado por URL e chave publicável (nenhuma chave secreta). SDK oficial fixado em 2.119.0. Login e cadastro por e-mail e senha; confirmação/recuperação usam o endereço do aplicativo como redirect. Configure **Authentication → URL Configuration** com a URL exata do Netlify. A entrega de e-mails depende das configurações de SMTP e dos limites do Supabase; o provedor Google ainda precisa de OAuth.

Em Início, entre na sua conta. Cada conta usa um IndexedDB e preferências próprios. O closet existente continua no modo local. Para migrá-lo, clique em **Importar closet local** e confirme. Nunca é enviado automaticamente. A sincronização automática envia metadados, preferências e fotos (bucket privado, caminho por usuário e hash) e consulta mudanças periodicamente. Revisões evitam sobrescrita silenciosa; em conflito, escolha uma versão conscientemente e faça backup antes. Não há merge automático de alterações simultâneas. O modo local permanece acessível sem login. A conta pode usar cache offline já autenticado, quando a sessão local estiver disponível. Sair mantém o cache separado nesta origem; não é criptografia local. Fotos não são enviadas ao GitHub. Arquivos antigos de fotos podem permanecer no bucket privado; limpeza de objetos órfãos será uma etapa futura. Evite dados pessoais em computadores compartilhados. Nenhum plano pago foi contratado.

## VESTE 4.1 — acesso obrigatório

O HTML inicia bloqueado. Sem uma sessão válida, somente a tela de apresentação, cadastro, login e recuperação está disponível. A inicialização do closet, IndexedDB e funcionalidades ocorre somente após a autenticação; os dados antigos locais são mantidos em sua base original e podem ser copiados após login em Início → Importar closet local. A sessão offline é aceita apenas enquanto não expirada. RLS e bucket privado continuam protegendo os dados remotos. O cache local não é criptografado. Login e recuperação dependem do serviço Auth e da entrega de e-mails configurada no projeto. 

## VESTE 4.2 — cadastro inteligente em lote

Meu closet → Cadastro em lote permite selecionar até 50 fotos (30 MB por arquivo, compactadas no navegador). Galeria de revisão com seleção/desmarcação, nomes e categorias obrigatórios, cores sugeridas localmente, detalhes opcionais, aplicação de categoria em lote, duplicidade exata de imagem e gravação local em transação única. Com Gemini conectado em Meu estilo, o app pede autorização para enviar as fotos selecionadas e classifica em grupos de quatro; sem chave a cor pode ser sugerida e a categoria pode ser manual, ou sugerida por nome de arquivo descritivo. Resultados ambíguos ficam pendentes; falhas da IA não apagam resultados. O lote ainda não salvo fica na memória da aba. Após salvar, as peças entram na sincronização da conta. Requer login; não altera as políticas de segurança existentes. Nenhum serviço pago ativado. Testar chave real e dispositivos móveis após publicação.

## VESTE 4.3 — lembrar chave Gemini no dispositivo

Meu estilo → Conectar IA → Lembrar chave neste dispositivo. Configuração em IndexedDB separado por conta, com AES-GCM e chave Web Crypto não exportável; identificador da conta autenticado no ciphertext. Não impede uso por scripts maliciosos da mesma origem ou acesso ao navegador. Não é incluída no backup nem enviada ao Supabase. Ao sair, a sessão é limpa e o registro lembrado permanece para o próximo login. Desconectar e esquecer chave remove o registro local. Use apenas em aparelho de confiança. Sem marcar, permanece apenas em memória. Teste em navegador real após deploy.

## VESTE 4.4 — revisão inteligente de duplicatas

Cadastro individual e em lote: foto idêntica, assinatura visual local (hash de diferenças horizontais/verticais, histograma de cores, amostragem de pixels, proporção, tentativa de recorte de fundo uniforme) e características cadastradas. Imagens exatas e suspeitas aparecem para revisão com miniaturas; sem exclusão automática. O lote verifica também as fotos anteriores do próprio lote e revalida antes de gravar. O usuário pode manter peças semelhantes. Comparação Gemini opcional, duas fotos por solicitação, com confirmação explícita; depende de chave e pode ter custo. Sem IA, a análise local continua. É possível haver falsos positivos e negativos, especialmente ângulos, peças lisas e fotos vestidas; os rótulos não expressam probabilidade calibrada. Nenhum dado adicional precisa ser salvo na nuvem. Detecta novas inserções (não faz deduplicação retroativa). Testes sintéticos: igualdade, diferenças de categoria/cor, mudança leve de posição/iluminação e metadados. Teste com fotos reais ainda necessário.
