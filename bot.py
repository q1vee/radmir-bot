import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import asyncio
import json
import os
import re

# ⚠️ ТОКЕН БОТА - ВСТАВЬТЕ СЮДА!
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# ⚠️ ID КАНАЛА ДЛЯ ЗАЯВОК (С КНОПКОЙ)
APPLICATION_CHANNEL_ID = 1470920804739846164

# ⚠️ ID КАНАЛА ДЛЯ ОТПРАВКИ ЗАЯВОК (КУДА ПРИХОДЯТ ЗАЯВКИ)
REVIEW_CHANNEL_ID = 1471236146230198394

# ⚠️ ID РОЛИ МОДЕРАТОРОВ
MODERATOR_ROLE_ID = 1471234453488795790


class FamilyModal(Modal, title="Заполните информацию о вашей семье"):
    gang_name = TextInput(
        label="Название группировки / мафии",
        placeholder="Пример: Los Santos Vagos",
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )

    name_cid = TextInput(
        label="Имя Фамилия | CID",
        placeholder="Пример: John Smith | 12345",
        required=True,
        max_length=50,
        style=discord.TextStyle.short
    )

    discord_id = TextInput(
        label="Discord ID",
        placeholder="Пример: 123456789012345678",
        required=True,
        max_length=20,
        style=discord.TextStyle.short,
        min_length=17
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем Discord ID
        try:
            user_id = int(self.discord_id.value)
            user = await interaction.client.fetch_user(user_id)
            user_mention = f"<@{user_id}>"
        except:
            user_mention = "❌ Пользователь не найден"
            user = None

        # СОЗДАЕМ EMBED ДЛЯ КАНАЛА С ЗАЯВКАМИ
        review_embed = discord.Embed(
            title="📋 НОВАЯ ЗАЯВКА",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        review_embed.add_field(
            name="👤 Заявитель",
            value=f"{interaction.user.mention}\nID: {interaction.user.id}",
            inline=True
        )

        review_embed.add_field(
            name="🔫 Название группировки/мафии",
            value=f"```{self.gang_name.value}```",
            inline=False
        )

        review_embed.add_field(
            name="👤 Имя Фамилия | CID",
            value=f"```{self.name_cid.value}```",
            inline=True
        )

        review_embed.add_field(
            name="🆔 Discord ID",
            value=f"```{self.discord_id.value}```\n{user_mention}",
            inline=True
        )

        review_embed.set_footer(
            text=f"Radmir МойДом • Ожидает проверки",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        # ОТПРАВЛЯЕМ ЗАЯВКУ В КАНАЛ ДЛЯ ПРОВЕРКИ
        review_channel = interaction.client.get_channel(REVIEW_CHANNEL_ID)
        if review_channel:
            view = ModerationView(interaction.user.id, interaction.user.name, self.gang_name.value)
            await review_channel.send(embed=review_embed, view=view)

            # ОТПРАВЛЯЕМ ПОДТВЕРЖДЕНИЕ ПОЛЬЗОВАТЕЛЮ
            await interaction.response.send_message(
                "✅ **Ваша заявка успешно отправлена!**\n"
                "Ожидайте решения администрации. Уведомление придет в личные сообщения.",
                ephemeral=True
            )

            # ОТПРАВЛЯЕМ ЛС ПОЛЬЗОВАТЕЛЮ
            try:
                dm_embed = discord.Embed(
                    title="✅ Заявка отправлена!",
                    description="Ваша заявка на получение роли владельца семьи была успешно отправлена.",
                    color=discord.Color.green()
                )
                dm_embed.add_field(
                    name="📝 Ваша заявка:",
                    value=f"**Группировка:** {self.gang_name.value}\n"
                          f"**Имя|CID:** {self.name_cid.value}\n"
                          f"**Discord ID:** {self.discord_id.value}",
                    inline=False
                )
                dm_embed.set_footer(text="Radmir МойДом • Ожидайте решения")

                await interaction.user.send(embed=dm_embed)
            except:
                # Если ЛС закрыты, ничего страшного
                pass
        else:
            await interaction.response.send_message("❌ Канал для проверки заявок не найден!", ephemeral=True)


class ModerationView(View):
    def __init__(self, applicant_id, applicant_name, gang_name):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.applicant_name = applicant_name
        self.gang_name = gang_name

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверка прав: только модераторы могут использовать кнопки"""
        moderator_role = interaction.guild.get_role(MODERATOR_ROLE_ID)
        if moderator_role in interaction.user.roles:
            return True

        await interaction.response.send_message(
            "❌ У вас нет прав для этого действия! Требуется роль модератора.",
            ephemeral=True
        )
        return False

    @discord.ui.button(label="✅ ПРИНЯТЬ", style=discord.ButtonStyle.green, custom_id="accept_role", emoji="✅", row=0)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        # Получаем embed
        embed = interaction.message.embeds[0]

        # Получаем пользователя
        member = interaction.guild.get_member(self.applicant_id)

        if member:
            # Загружаем конфиг роли
            role_id = None
            if os.path.exists('role_config.json'):
                with open('role_config.json', 'r') as f:
                    data = json.load(f)
                    role_id = data.get(str(interaction.guild_id))

            if role_id:
                role = interaction.guild.get_role(role_id)
                if role:
                    await member.add_roles(role)

                    # ОБНОВЛЯЕМ EMBED
                    embed.color = discord.Color.green()
                    new_embed = embed.copy()
                    new_embed.set_footer(text=f"Radmir МойДом • Принято модератором {interaction.user.name}",
                                         icon_url=interaction.user.avatar.url)

                    # Отправляем сообщение об одобрении в тот же канал
                    accept_embed = discord.Embed(
                        title="✅ ЗАЯВКА ОДОБРЕНА",
                        description=f"**Заявитель:** {member.mention}\n"
                                    f"**Группировка:** {self.gang_name}\n"
                                    f"**Модератор:** {interaction.user.mention}\n"
                                    f"**Роль:** {role.mention}",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    accept_embed.set_footer(text="Radmir МойДом")

                    await interaction.message.edit(embed=new_embed, view=None)
                    await interaction.response.send_message(embed=accept_embed)

                    # УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ В ЛС
                    try:
                        dm_embed = discord.Embed(
                            title="✅ ЗАЯВКА ОДОБРЕНА!",
                            description=f"Ваша заявка на роль владельца семьи была **ОДОБРЕНА**!",
                            color=discord.Color.green()
                        )
                        dm_embed.add_field(name="🏢 Группировка", value=self.gang_name, inline=False)
                        dm_embed.add_field(name="👮 Модератор", value=interaction.user.name, inline=False)
                        dm_embed.add_field(name="🎭 Роль", value=role.mention, inline=False)
                        dm_embed.set_footer(text="Radmir МойДом")

                        await member.send(embed=dm_embed)
                    except:
                        pass
                else:
                    await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Роль не настроена! Используйте `/role`", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Пользователь не найден на сервере!", ephemeral=True)

    @discord.ui.button(label="❌ ОТКЛОНИТЬ", style=discord.ButtonStyle.red, custom_id="deny_role", emoji="❌", row=0)
    async def deny_button(self, interaction: discord.Interaction, button: Button):
        # Создаем модальное окно для причины отказа
        class DenyModal(Modal, title="Отклонение заявки"):
            reason = TextInput(
                label="Причина отказа",
                placeholder="Укажите причину отклонения заявки",
                required=True,
                style=discord.TextStyle.paragraph,
                max_length=500
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                # Получаем embed
                embed = modal_interaction.message.embeds[0]

                # ОБНОВЛЯЕМ EMBED
                embed.color = discord.Color.red()
                new_embed = embed.copy()
                new_embed.set_footer(text=f"Radmir МойДом • Отклонено модератором {modal_interaction.user.name}",
                                     icon_url=modal_interaction.user.avatar.url)

                # Отправляем сообщение об отказе
                deny_embed = discord.Embed(
                    title="❌ ЗАЯВКА ОТКЛОНЕНА",
                    description=f"**Заявитель:** <@{self.applicant_id}>\n"
                                f"**Группировка:** {self.gang_name}\n"
                                f"**Модератор:** {modal_interaction.user.mention}\n"
                                f"**Причина:** {self.reason.value}",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                deny_embed.set_footer(text="Radmir МойДом")

                await modal_interaction.message.edit(embed=new_embed, view=None)
                await modal_interaction.response.send_message(embed=deny_embed)

                # УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ В ЛС
                try:
                    member = modal_interaction.guild.get_member(self.applicant_id)
                    if member:
                        dm_embed = discord.Embed(
                            title="❌ ЗАЯВКА ОТКЛОНЕНА",
                            description=f"Ваша заявка на роль владельца семьи была **ОТКЛОНЕНА**.",
                            color=discord.Color.red()
                        )
                        dm_embed.add_field(name="🏢 Группировка", value=self.gang_name, inline=False)
                        dm_embed.add_field(name="❌ Причина", value=self.reason.value, inline=False)
                        dm_embed.add_field(name="👮 Модератор", value=modal_interaction.user.name, inline=False)
                        dm_embed.set_footer(text="Radmir МойДом")

                        await member.send(embed=dm_embed)
                except:
                    pass

        await interaction.response.send_modal(DenyModal())

    @discord.ui.button(label="⏳ ОЖИДАЕТ", style=discord.ButtonStyle.secondary, custom_id="pending_role", emoji="⏳",
                       row=0, disabled=True)
    async def pending_button(self, interaction: discord.Interaction, button: Button):
        pass


class FamilyButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👑 Получить роль", style=discord.ButtonStyle.primary, custom_id="get_family_role",
                       emoji="👑")
    async def family_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FamilyModal())


class FamilyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.setup_done = False

    async def on_ready(self):
        await self.wait_until_ready()
        await self.tree.sync()

        # Добавляем постоянные представления
        self.add_view(FamilyButtonView())

        print(f"✅ Бот {self.user} запущен!")
        print(f"Серверов: {len(self.guilds)}")

        # Настраиваем канал для заявок
        await self.setup_application_channel()

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Radmir МойДом | Заявки"
            )
        )

    async def setup_application_channel(self):
        """Настройка канала для заявок"""
        if self.setup_done:
            return

        for guild in self.guilds:
            channel = guild.get_channel(APPLICATION_CHANNEL_ID)
            if channel:
                # ОЧИЩАЕМ КАНАЛ ОТ СТАРЫХ СООБЩЕНИЙ
                async for message in channel.history(limit=100):
                    if message.author == self.user:
                        await message.delete()
                    await asyncio.sleep(0.5)

                # Отправляем новое сообщение
                embed = discord.Embed(
                    title="👑 Получение роли владельца семьи",
                    description="**Для получения роли нажмите на кнопку ниже и заполните форму**\n\n"
                                "📋 **Требования:**\n"
                                "• Указать название группировки/мафии\n"
                                "• Указать Имя Фамилию и CID\n"
                                "• Указать ваш Discord ID\n\n"
                                "⚠️ Заявки, заполненные некорректно, будут отклоняться!\n"
                                "⏳ Ожидайте решения в личных сообщениях.",
                    color=discord.Color.blue()
                )

                embed.set_footer(text="Radmir МойДом")
                embed.timestamp = discord.utils.utcnow()

                await channel.send(embed=embed, view=FamilyButtonView())
                print(f"✅ Отправлено сообщение в канал {channel.name}")
                self.setup_done = True


bot = FamilyBot()


@bot.event
async def on_message(message):
    """Блокировка сообщений в канале заявок"""
    if message.author.bot:
        return

    if message.channel.id == APPLICATION_CHANNEL_ID:
        # Удаляем сообщение пользователя
        await message.delete()

        # Отправляем уведомление
        embed = discord.Embed(
            title="❌ Писать в этом канале запрещено",
            description="**Используйте кнопку 👑 Получить роль для подачи заявки**\n\n"
                        "Все заявки рассматриваются в течение 24 часов.\n"
                        "Решение придет в личные сообщения.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Radmir МойДом")

        warn_msg = await message.channel.send(embed=embed)

        # Удаляем уведомление через 5 секунд
        await asyncio.sleep(5)
        await warn_msg.delete()


@bot.tree.command(name="role", description="Установить роль для выдачи")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="Роль для выдачи владельцам семей")
async def role_command(interaction: discord.Interaction, role: discord.Role):
    """Установка роли для автоматической выдачи"""

    data = {}
    if os.path.exists('role_config.json'):
        with open('role_config.json', 'r') as f:
            data = json.load(f)

    data[str(interaction.guild_id)] = role.id

    with open('role_config.json', 'w') as f:
        json.dump(data, f, indent=4)

    embed = discord.Embed(
        title="✅ Роль установлена",
        description=f"При одобрении заявки будет выдаваться роль {role.mention}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Radmir МойДом")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="clear", description="Очистить канал заявок")
@app_commands.default_permissions(administrator=True)
async def clear_command(interaction: discord.Interaction):
    """Очистка канала с заявками"""

    channel = interaction.guild.get_channel(APPLICATION_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)
        return

    await interaction.response.send_message("🧹 Начинаю очистку канала...", ephemeral=True)

    deleted = 0
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()
            deleted += 1
            await asyncio.sleep(0.5)

    # Отправляем новое сообщение
    embed = discord.Embed(
        title="👑 Получение роли владельца семьи",
        description="**Для получения роли нажмите на кнопку ниже и заполните форму**\n\n"
                    "📋 **Требования:**\n"
                    "• Указать название группировки/мафии\n"
                    "• Указать Имя Фамилию и CID\n"
                    "• Указать ваш Discord ID\n\n"
                    "⚠️ Заявки, заполненные некорректно, будут отклоняться!\n"
                    "⏳ Ожидайте решения в личных сообщениях.",
        color=discord.Color.blue()
    )

    embed.set_footer(text="Radmir МойДом")
    embed.timestamp = discord.utils.utcnow()

    await channel.send(embed=embed, view=FamilyButtonView())

    await interaction.followup.send(f"✅ Канал очищен. Удалено {deleted} сообщений", ephemeral=True)


# Запуск бота
if __name__ == "__main__":
    bot.run(BOT_TOKEN)