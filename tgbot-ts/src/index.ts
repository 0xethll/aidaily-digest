import { Bot, Context, webhookCallback } from 'grammy';

export interface Env {
	BOT_INFO: string;
	BOT_TOKEN: string;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const bot = new Bot(env.BOT_TOKEN, { botInfo: JSON.parse(env.BOT_INFO) });

		bot.command('start', async (ctx: Context) => {
			await ctx.reply('Hello, world!');
		});

		return webhookCallback(bot, 'cloudflare-mod')(request);
	},
} satisfies ExportedHandler<Env>;
