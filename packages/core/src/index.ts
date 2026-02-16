export interface ITenantResolver {
  resolve(request: any): Promise<string>;
}

export class SingleTenantResolver implements ITenantResolver {
  async resolve(request: any): Promise<string> {
    console.log('Resolving tenant in Single Tenant Mode (OSS)');
    return 'default-tenant';
  }
}

export interface IExampleService {
  doWork(): void;
}

export class BaseExampleService implements IExampleService {
  doWork(): void {
    console.log('Core work executed.');
  }
}
