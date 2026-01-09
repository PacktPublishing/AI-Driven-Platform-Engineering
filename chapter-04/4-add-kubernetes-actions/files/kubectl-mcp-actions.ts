import { createBackendModule } from '@backstage/backend-plugin-api';
import { actionsRegistryServiceRef } from '@backstage/backend-plugin-api/alpha';
import { spawn } from 'child_process';
import { z } from 'zod';

// Helper function to execute kubectl commands
async function execKubectl(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const kubectl = spawn('kubectl', args);
    let stdout = '';
    let stderr = '';

    kubectl.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    kubectl.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    kubectl.on('close', (code) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(stderr || `kubectl exited with code ${code}`));
      }
    });

    kubectl.on('error', (err) => {
      reject(err);
    });
  });
}

export default createBackendModule({
  pluginId: 'mcp-actions',
  moduleId: 'kubectl-actions',
  register(env) {
    env.registerInit({
      deps: {
        actionsRegistry: actionsRegistryServiceRef,
      },
      async init({ actionsRegistry }) {
        // Register kubectl get pods action
        actionsRegistry.register({
          name: 'kubectl_get_pods',
          title: 'Get Kubernetes Pods',
          description: 'Get pods in a Kubernetes namespace',
          schema: {
            input: (zod: typeof z) =>
              zod.object({
                namespace: zod.string().default('default').describe('The Kubernetes namespace'),
              }),
            output: (zod: typeof z) =>
              zod.object({
                result: zod.string().describe('JSON output of kubectl get pods'),
              }),
          },
          action: async ({ input }) => {
            const result = await execKubectl(['get', 'pods', '-n', input.namespace, '-o', 'json']);
            return { output: { result } };
          },
        });

        // Register kubectl get deployments action
        actionsRegistry.register({
          name: 'kubectl_get_deployments',
          title: 'Get Kubernetes Deployments',
          description: 'Get deployments in a Kubernetes namespace',
          schema: {
            input: (zod: typeof z) =>
              zod.object({
                namespace: zod.string().default('default').describe('The Kubernetes namespace'),
              }),
            output: (zod: typeof z) =>
              zod.object({
                result: zod.string().describe('JSON output of kubectl get deployments'),
              }),
          },
          action: async ({ input }) => {
            const result = await execKubectl(['get', 'deployments', '-n', input.namespace, '-o', 'json']);
            return { output: { result } };
          },
        });

        // Register kubectl get services action
        actionsRegistry.register({
          name: 'kubectl_get_services',
          title: 'Get Kubernetes Services',
          description: 'Get services in a Kubernetes namespace',
          schema: {
            input: (zod: typeof z) =>
              zod.object({
                namespace: zod.string().default('default').describe('The Kubernetes namespace'),
              }),
            output: (zod: typeof z) =>
              zod.object({
                result: zod.string().describe('JSON output of kubectl get services'),
              }),
          },
          action: async ({ input }) => {
            const result = await execKubectl(['get', 'services', '-n', input.namespace, '-o', 'json']);
            return { output: { result } };
          },
        });

        // Register kubectl describe pod action
        actionsRegistry.register({
          name: 'kubectl_describe_pod',
          title: 'Describe Kubernetes Pod',
          description: 'Describe a specific pod in a Kubernetes namespace',
          schema: {
            input: (zod: typeof z) =>
              zod.object({
                pod_name: zod.string().describe('The name of the pod to describe'),
                namespace: zod.string().default('default').describe('The Kubernetes namespace'),
              }),
            output: (zod: typeof z) =>
              zod.object({
                result: zod.string().describe('Output of kubectl describe pod'),
              }),
          },
          action: async ({ input }) => {
            const result = await execKubectl(['describe', 'pod', input.pod_name, '-n', input.namespace]);
            return { output: { result } };
          },
        });
      },
    });
  },
});
