/**
 * Backstage backend module that registers `strands-proxy` as an agent type
 * with the AWS GenAI plugin. When configured, an agent of this type forwards
 * the user's message to an external HTTP endpoint that speaks the Strands
 * agent runtime's `/invoke` contract — letting Backstage render the chat UI
 * for an agent whose model loop runs in a separate service.
 *
 * Chapter 6 of the book: this is the adapter that materializes Figure 6.3,
 * "Backstage UI as a trigger source for the agent runtime."
 *
 * Config example:
 *   genai:
 *     agents:
 *       platform-ops:
 *         description: Platform operations agent (proxy)
 *         strands-proxy:
 *           url: http://localhost:18080
 */
import {
  coreServices,
  createBackendModule,
} from '@backstage/backend-plugin-api';
import {
  agentTypeExtensionPoint,
  type AgentConfig,
  type AgentType,
} from '@aws/genai-plugin-for-backstage-node';

class StrandsProxyAgent implements AgentType {
  constructor(
    private readonly url: string,
    private readonly logger: { info: Function; warn: Function; error: Function },
  ) {}

  async stream(
    userMessage: string,
    sessionId: string,
    _newSession: boolean,
    _agentActions: any[],
    _peerAgentTools: any[],
    _logger: any,
    options: { userEntityRef?: { kind: string; namespace: string; name: string } },
  ): Promise<ReadableStream<any>> {
    const userId = options.userEntityRef
      ? `${options.userEntityRef.kind}:${options.userEntityRef.namespace}/${options.userEntityRef.name}`
      : 'guest';

    this.logger.info(
      `[strands-proxy] forwarding to ${this.url}/invoke session=${sessionId} user=${userId}`,
    );

    const response = await this.callInvoke(userMessage, sessionId, userId);

    return new ReadableStream({
      start(controller) {
        if (response.error) {
          controller.enqueue({ type: 'ErrorEvent', message: response.error });
        } else {
          // Single-shot stream: emit the whole response as one chunk, then end.
          // Real streaming would require Strands to expose SSE/chunked output
          // and the adapter to forward token-by-token; left as an exercise.
          controller.enqueue({ type: 'ChunkEvent', token: response.text });
          controller.enqueue({ type: 'ResponseEvent', sessionId });
        }
        controller.close();
      },
    });
  }

  async generate(
    prompt: string,
    sessionId: string,
    _agentActions: any[],
    _peerAgentTools: any[],
    _logger: any,
    _options: any,
  ): Promise<{ output: any }> {
    this.logger.info(
      `[strands-proxy] generate session=${sessionId} url=${this.url}`,
    );
    const response = await this.callInvoke(prompt, sessionId, 'guest');
    return { output: response.text || response.error };
  }

  private async callInvoke(
    intent: string,
    sessionId: string,
    userId: string,
  ): Promise<{ text?: string; error?: string }> {
    try {
      const r = await fetch(`${this.url}/invoke`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ intent, session_id: sessionId, user_id: userId }),
      });
      if (!r.ok) {
        const body = await r.text();
        return { error: `Strands /invoke returned ${r.status}: ${body}` };
      }
      const data = (await r.json()) as { response: string };
      return { text: data.response };
    } catch (e: any) {
      this.logger.error(`[strands-proxy] fetch failed: ${e.message ?? e}`);
      return { error: `Could not reach Strands runtime: ${e.message ?? e}` };
    }
  }
}

export default createBackendModule({
  pluginId: 'aws-genai',
  moduleId: 'strands-proxy-agent',
  register(reg) {
    reg.registerInit({
      deps: {
        agentType: agentTypeExtensionPoint,
        logger: coreServices.logger,
      },
      async init({ agentType, logger }) {
        agentType.addAgentType({
          getTypeName: () => 'strands-proxy',
          create: async (agentConfig: AgentConfig) => {
            // The plugin attaches the raw Backstage Config under .config.
            // strands-proxy.url comes from the YAML.
            const url = (agentConfig as any).config.getString(
              'strands-proxy.url',
            );
            logger.info(
              `[strands-proxy] registered agent ${agentConfig.name} url=${url}`,
            );
            return new StrandsProxyAgent(url, logger);
          },
        });
      },
    });
  },
});
