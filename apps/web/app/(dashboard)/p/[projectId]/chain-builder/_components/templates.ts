import type { Node, Edge } from "reactflow";
import type { RequestNodeData } from "./nodes";

export interface ChainTemplate {
  name: string;
  description: string;
  nodes: Node<RequestNodeData>[];
  edges: Edge[];
}

export const CHAIN_TEMPLATES: ChainTemplate[] = [
  {
    name: "Login \u2192 Transfer \u2192 Verify",
    description: "Giriş yap, para transferi gerceklestir, bakiye dogrula",
    nodes: [
      {
        id: "t1-login",
        type: "request",
        position: { x: 50, y: 120 },
        data: {
          label: "Login",
          method: "POST",
          path: "/api/v1/auth/login",
          headers: { "Content-Type": "application/json" },
          body: '{"username": "{{user}}", "password": "{{pass}}"}',
          extractions: [
            { json_path: "$.access_token", variable_name: "auth_token" },
            { json_path: "$.user.id", variable_name: "user_id" },
          ],
          assertions: [{ type: "status_code", expected: 200, operator: "equals" }],
        },
      },
      {
        id: "t1-transfer",
        type: "request",
        position: { x: 380, y: 120 },
        data: {
          label: "Transfer",
          method: "POST",
          path: "/api/v1/accounts/transfer",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer {{auth_token}}",
          },
          body: '{"from_account": "{{account_id}}", "to_account": "TR123456", "amount": 100.00}',
          extractions: [
            { json_path: "$.transaction_id", variable_name: "tx_id" },
          ],
          assertions: [
            { type: "status_code", expected: 200, operator: "equals" },
          ],
        },
      },
      {
        id: "t1-verify",
        type: "request",
        position: { x: 710, y: 120 },
        data: {
          label: "Verify Balance",
          method: "GET",
          path: "/api/v1/accounts/{{account_id}}/balance",
          headers: { Authorization: "Bearer {{auth_token}}" },
          body: "",
          extractions: [],
          assertions: [
            { type: "status_code", expected: 200, operator: "equals" },
            { type: "json_path", expected: "number", operator: "exists" },
          ],
        },
      },
    ],
    edges: [
      {
        id: "t1-e1",
        source: "t1-login",
        target: "t1-transfer",
        label: "auth_token",
        animated: true,
        style: { stroke: "#6366f1" },
      },
      {
        id: "t1-e2",
        source: "t1-transfer",
        target: "t1-verify",
        label: "tx_id",
        animated: true,
        style: { stroke: "#6366f1" },
      },
    ],
  },
  {
    name: "Login \u2192 Account List \u2192 Balance Check",
    description: "Giriş yap, hesap listesi al, bakiye kontrol et",
    nodes: [
      {
        id: "t2-login",
        type: "request",
        position: { x: 50, y: 120 },
        data: {
          label: "Login",
          method: "POST",
          path: "/api/v1/auth/login",
          headers: { "Content-Type": "application/json" },
          body: '{"username": "{{user}}", "password": "{{pass}}"}',
          extractions: [
            { json_path: "$.access_token", variable_name: "auth_token" },
          ],
          assertions: [{ type: "status_code", expected: 200, operator: "equals" }],
        },
      },
      {
        id: "t2-accounts",
        type: "request",
        position: { x: 380, y: 120 },
        data: {
          label: "Account List",
          method: "GET",
          path: "/api/v1/accounts",
          headers: { Authorization: "Bearer {{auth_token}}" },
          body: "",
          extractions: [
            { json_path: "$.accounts[0].id", variable_name: "account_id" },
          ],
          assertions: [
            { type: "status_code", expected: 200, operator: "equals" },
          ],
        },
      },
      {
        id: "t2-balance",
        type: "request",
        position: { x: 710, y: 120 },
        data: {
          label: "Balance Check",
          method: "GET",
          path: "/api/v1/accounts/{{account_id}}/balance",
          headers: { Authorization: "Bearer {{auth_token}}" },
          body: "",
          extractions: [],
          assertions: [
            { type: "status_code", expected: 200, operator: "equals" },
            { type: "json_path", expected: 0, operator: "gt" },
          ],
        },
      },
    ],
    edges: [
      {
        id: "t2-e1",
        source: "t2-login",
        target: "t2-accounts",
        label: "auth_token",
        animated: true,
        style: { stroke: "#6366f1" },
      },
      {
        id: "t2-e2",
        source: "t2-accounts",
        target: "t2-balance",
        label: "account_id",
        animated: true,
        style: { stroke: "#6366f1" },
      },
    ],
  },
];
