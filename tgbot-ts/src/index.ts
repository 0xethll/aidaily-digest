import { Bot, Context, webhookCallback } from 'grammy';
import { UserFromGetMe } from 'grammy/types';

export interface Env {
	BOT_INFO: UserFromGetMe;
	BOT_TOKEN: string;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const bot = new Bot(env.BOT_TOKEN, { botInfo: env.BOT_INFO });

		bot.command('start', async (ctx: Context) => {
			await ctx.reply('Hello, world!');
		});

		return webhookCallback(bot, 'cloudflare-mod')(request);
	},
} satisfies ExportedHandler<Env>;
