const pushEvent = require('D:/todo-bot/tests/fixtures/payloads/custom-push.json')
const { gimmeApp, loadConfig, loadDiff } = require('D:/todo-bot/tests/helpers')

const stringify = require('csv-stringify')
const { truncate } = require('D:/todo-bot/lib/utils/helpers')
const fs = require('fs')
const path = require('path')
var stream = fs.createWriteStream("issues_pre_bot.csv", {flags:'a'});

describe('push-handler', () => {
  let app, github
  let event = { name: 'push', payload: pushEvent }

  beforeEach(() => {
    const gimme = gimmeApp()
    app = gimme.app
    github = gimme.github
  })
