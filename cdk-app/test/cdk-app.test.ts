import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as CdkApp from '../lib/calm_chatbot_stack';

test('Lambda Function Created', () => {
  const app = new cdk.App();
  const stack = new CdkApp.CalmChatbotStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::Lambda::Function', {
    MemorySize: 256,
    Timeout: 30,
  });
});

test('DynamoDB Tables Created', () => {
  const app = new cdk.App();
  const stack = new CdkApp.CalmChatbotStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  template.resourceCountIs('AWS::DynamoDB::Table', 3); // Sessions, Messages, and Payments tables
});

test('API Gateway Created', () => {
  const app = new cdk.App();
  const stack = new CdkApp.CalmChatbotStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::ApiGateway::RestApi', {
    Name: 'ChatAPI',
  });
});

test('Cognito User Pool Created', () => {
  const app = new cdk.App();
  const stack = new CdkApp.CalmChatbotStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::Cognito::UserPool', {
    UserPoolName: 'CalmChatbotUserPool',
  });
});
