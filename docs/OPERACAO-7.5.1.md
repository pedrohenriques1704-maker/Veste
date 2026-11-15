# VESTE 7.5.1 — Operação e atendimento

## Antes de convidar usuários
- Confirmar nome/identificação do controlador e canal de privacidade público que funcione sem login. Atualizar a política de privacidade e os termos; revisar bases legais, prazos de retenção, serviços internacionais e dados de terceiros com orientação jurídica adequada.
- Testar login (Google e e-mail), perfil de nova conta, logout/login, cadastro de roupa, criação/registro de look, câmera/galeria do Diário, sincronização e exportação em Android e iOS. Testar feedback, resposta no Admin e permissões de conta não administrativa. Não utilizar dados ou fotos de terceiros para testes sem autorização.
- Confirmar os limites atuais e preços do plano no painel de Supabase e Netlify e configurar alertas; os números do Admin são armazenamento e contagens, não faturamento.
- Revisar a fila de atendimento diariamente durante os testes. Responder cada protocolo pelo Admin e acompanhar as solicitações de dados dentro dos prazos aplicáveis. Não marcar exclusão como concluída enquanto não houver execução e verificação.

## Solicitações de exclusão: procedimento manual restrito
1. Abrir Admin > Feedback e atendimento > Exclusão. Confirmar identidade, escopo, protocolo e UUID da conta. Mudar para Em análise e responder. Oferecer ao titular a exportação do closet e dos meses do diário e orientação para apagar cache/arquivos locais após a exclusão. Não solicitar senha ou chave Gemini.
2. Conferir se a conta não é o único administrador. Registrar o tratamento mínimo necessário e eventual obrigação legal de retenção. Não armazenar fotos ou cópias do closet fora dos serviços para execução.
3. Impedir novos logins/atividades e revogar sessões conforme mecanismos administrativos do Supabase; tokens de acesso podem continuar válidos até expirar. Não confundir sair do aplicativo com exclusão.
4. Usar o painel Storage ou a API oficial de Storage com autorização administrativa para remover somente os arquivos dentro da pasta UUID confirmada em `veste-photos` (inclui `diary/`) e `veste-try-private`. Não remover linhas diretamente de `storage.objects`; isso não remove os objetos reais. Conferir subpastas e listar novamente após a limpeza.
5. Eliminar os eventos de navegação atribuíveis à conta: a chave é o HMAC de UUID com o salt da configuração de analytics. Use a operação administrativa restrita, parametrizada com UUID exato, sem imprimir o salt. Os cliques comerciais atuais utilizam hash por minuto sem mapeamento direto; avaliar tratamento/retencão desses registros antes de prometer eliminação integral.
6. Após confirmação e limpeza, excluir a conta pelo painel Authentication > Users. As tabelas com FK ON DELETE CASCADE removem snapshots do closet, versões, diário, tickets, diagnósticos e demais registros vinculados por FK. Não apagar registros de outras contas ou dados comerciais agregados. Verificar se sobrou armazenamento e se as tabelas vinculadas ficaram vazias para o UUID. Confirmar retenção de backups com os provedores.
7. Comunicar o resultado por canal de contato previamente validado. O aplicativo não executa esse procedimento automaticamente. O ticket é excluído em cascata com a conta: não prometer consulta após a exclusão. Confirmar o atendimento fora da conta, respeitando a minimização e os prazos aplicáveis.

## Indicadores
- Contagem de contas, onboarding concluído, >=10 peças reais, registro de pelo menos um uso real, diário com foto e closets sincronizados: fotografia acumulada dos dados operacionais, não análise de coorte. O Admin não acessa fotos ou detalhes de preferências para esses indicadores.
- Navegação e retorno: dados de usuários com autorização de estatísticas.
- Diagnósticos: autorização independente, código de categoria sem texto de erro, conta e minuto; retenção de 30 dias. Não confundir ausência de eventos com ausência de erros.
- Feedback e solicitações: dados de atendimento, com mensagens e respostas; somente usuários autenticados envolvidos e administradores autorizados.
