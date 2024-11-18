#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { CalmChatbotStack } from '../lib/calm_chatbot_stack';

const app = new cdk.App();
new CalmChatbotStack(app, 'CalmChatbotStack');
