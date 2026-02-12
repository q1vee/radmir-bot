import discord
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
from datetime import datetime
import os
import json

# 📌 ТОКЕН БЕРЕМ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
TOKEN = os.environ.get('TOKEN')

# 📌 ID КАНАЛА, ГДЕ ПОЛЬЗОВАТЕЛЬ СОЗДАЕТ ВЕТКУ (с кнопкой)
SOURCE_CHANNEL_ID = 1470927826118115328

# 📌 ID КАНАЛА, КУДА ПРИХОДЯТ ВСЕ ЗАЯВКИ (для организаторов)
TICKET_REQUESTS_CHANNEL_ID = 1471567835527643277

# 📌 ID КАТЕГОРИИ ДЛЯ ПРИВАТНЫХ ВЕТОК
TICKET_CATEGORY_ID = 1471565535102898378

# 📌 ID РОЛИ ОРГАНИЗАТОРОВ (кто получает уведомления)
MODERATOR_ROLE_ID = 1471234453488795790

class TicketModal(Modal, title="Получение /mp кода"):
    """Модальное окно с формой"""
    
    group_name = TextInput(
        label="Название команды/группировки/мафии",
        placeholder="Пример: Los Santos Vagos, Банда, RFL",
        required=True,
        max_length=100,
        style=discord.TextStyle.short
    )
    
    discord_id = TextInput(
        label="Ваш Discord ID",
        placeholder="123456789012345678",
        required=True,
        max_length=20
    )
    
    comment = TextInput(
        label="Комментарий (необязательно)",
        placeholder="Дополнительная информация",
        required=False,
        max_length=100,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            ticket_number = str(int(datetime.now().timestamp()))[-6:]
            
            source_channel = interaction.guild.get_channel(SOURCE_CHANNEL_ID)
            if not source_channel:
                await interaction.followup.send("❌ Исходный канал не найден!", ephemeral=True)
                return
            
            requests_channel = interaction.guild.get_channel(TICKET_REQUESTS_CHANNEL_ID)
            if not requests_channel:
                await interaction.followup.send("❌ Канал для заявок не найден!", ephemeral=True)
                return
            
            moderator_role = interaction.guild.get_role(MODERATOR_ROLE_ID)
            role_mention = moderator_role.mention if moderator_role else "@Организатор"
            
            # Embed для канала заявок
            request_embed = discord.Embed(
                title="🎫 НОВАЯ ЗАЯВКА НА /MP КОД",
                description=f"**{role_mention}**",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            request_embed.add_field(name="👤 Пользователь", value=f"{interaction.user.mention}\nID: {interaction.user.id}", inline=True)
            request_embed.add_field(name="🏢 Название", value=f"```{self.group_name.value}```", inline=False)
            request_embed.add_field(name="🆔 Discord ID", value=f"`{self.discord_id.value}`", inline=True)
            request_embed.add_field(name="📝 Комментарий", value=f"{self.comment.value or 'Нет'}", inline=False)
            request_embed.add_field(name="📋 Номер заявки", value=f"`#{ticket_number}`", inline=True)
            request_embed.set_footer(text="Radmir МойДом | Нажмите кнопку ниже чтобы ответить")
            
            view = RespondToUserView(
                user_id=interaction.user.id, 
                ticket_number=ticket_number, 
                group_name=self.group_name.value,
                discord_id=self.discord_id.value, 
                comment=self.comment.value or "Нет"
            )
            
            await requests_channel.send(
                content=f"{role_mention} — Новая заявка на /mp код!",
                embed=request_embed,
                view=view
            )
            
            # Подтверждение пользователю
            confirm_embed = discord.Embed(
                title="❤️ Ваша заявка отправлена!",
                description=f"**Номер заявки:** #{ticket_number}\n"
                          f"**Команда/группировка:** {self.group_name.value}\n"
                          f"**Статус:** ⏳ Ожидает ответа организатора\n\n"
                          f"Организатор свяжется с вами в **личных сообщениях**.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            confirm_embed.set_footer(text="Radmir МойДом | MP код")
            
            await interaction.followup.send(embed=confirm_embed, ephemeral=True)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send(f"❌ Ошибка: {str(e)[:100]}", ephemeral=True)

class SendCodeModal(Modal):
    def __init__(self, user_id: int, ticket_number: str, group_name: str, discord_id: str, comment: str, moderator_name: str):
        super().__init__(title=f"Отправка /mp кода | Заявка #{ticket_number}")
        self.user_id = user_id
        self.ticket_number = ticket_number
        self.group_name = group_name
        self.discord_id = discord_id
        self.comment = comment
        self.moderator_name = moderator_name
        
        self.code = TextInput(label="Код от /mp", placeholder="1234-5678", required=True, max_length=20)
        self.add_item(self.code)
    
    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.guild.get_member(self.user_id)
        if user:
            try:
                # Отправляем код в ЛС
                dm_embed = discord.Embed(
                    title="🎫 Ваш /mp код получен!",
                    description=f"**Номер заявки:** #{self.ticket_number}\n"
                              f"**Команда/группировка:** {self.group_name}\n\n"
                              f"🔑 **Ваш код:** `{self.code.value}`\n\n"
                              f"Используйте его в игре!",
                    color=discord.Color.green()
                )
                dm_embed.set_footer(text=f"Отправил: {self.moderator_name} | Radmir МойДом")
                await user.send(embed=dm_embed)
                
                # ВЫДАЧА РОЛИ ПОСЛЕ ОТПРАВКИ КОДА
                try:
                    # Загружаем ID роли из файла
                    role_id = None
                    if os.path.exists('role_config.json'):
                        with open('role_config.json', 'r') as f:
                            data = json.load(f)
                            role_id = data.get(str(interaction.guild_id))
                    
                    if role_id:
                        role = interaction.guild.get_role(role_id)
                        if role:
                            await user.add_roles(role)
                            print(f"✅ Роль {role.name} выдана {user.name}")
                except Exception as e:
                    print(f"❌ Ошибка при выдаче роли: {e}")
                
                # Обновляем embed
                embed = interaction.message.embeds[0]
                new_embed = discord.Embed(title="✅ ЗАЯВКА ОБРАБОТАНА", color=discord.Color.green(), timestamp=datetime.utcnow())
                for field in embed.fields:
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                new_embed.add_field(name="📨 Код отправлен", value=f"`{self.code.value}`\nОтправил: {interaction.user.mention}", inline=False)
                new_embed.set_footer(text=f"Radmir МойДом | Обработано: {datetime.utcnow().strftime('%H:%M %d.%m.%Y')}")
                
                await interaction.message.edit(embed=new_embed, view=None)
                await interaction.response.send_message(f"✅ Код отправлен пользователю {user.mention}\n✅ Роль выдана!", ephemeral=True)
                
            except discord.Forbidden:
                await interaction.response.send_message("❌ Не могу отправить ЛС пользователю. У него закрыты личные сообщения!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Ошибка: {str(e)[:100]}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Пользователь не найден на сервере!", ephemeral=True)

class RespondToUserView(View):
    def __init__(self, user_id: int, ticket_number: str, group_name: str, discord_id: str, comment: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_number = ticket_number
        self.group_name = group_name
        self.discord_id = discord_id
        self.comment = comment
    
    @discord.ui.button(label="✏️ Ответить пользователю", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="respond_to_user")
    async def respond_button(self, interaction: discord.Interaction, button: Button):
        moderator_role = interaction.guild.get_role(MODERATOR_ROLE_ID)
        if moderator_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Только организаторы могут отвечать на заявки!", ephemeral=True)
            return
        
        await interaction.response.send_modal(
            SendCodeModal(
                user_id=self.user_id,
                ticket_number=self.ticket_number,
                group_name=self.group_name,
                discord_id=self.discord_id,
                comment=self.comment,
                moderator_name=interaction.user.name
            )
        )

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="📩 Получить /mp код", style=discord.ButtonStyle.primary, emoji="📩", custom_id="ticket_create_button")
    async def ticket_button(self, interaction: discord.Interaction, button: Button):
        if interaction.channel.id != SOURCE_CHANNEL_ID:
            await interaction.response.send_message(f"❌ Используйте эту кнопку в канале <#{SOURCE_CHANNEL_ID}>", ephemeral=True)
            return
        await interaction.response.send_modal(TicketModal())

class TicketBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        self.add_view(TicketButtonView())
        await self.tree.sync()
        print("✅ Persistent views загружены")
    
    async def on_ready(self):
        print(f"✅ Бот {self.user} запущен!")
        print(f"ID бота: {self.user.id}")
        print(f"Серверов: {len(self.guilds)}")
        await self.send_ticket_panel()
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Radmir МойДом | MP код"))
    
    async def send_ticket_panel(self):
        for guild in self.guilds:
            channel = guild.get_channel(SOURCE_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="🎮 ПОЛУЧЕНИЕ /MP КОДА",
                    description="**🔹 Нужен код от /mp?**\n\nНажми на кнопку ниже — заявка будет отправлена организаторам.\nОрганизатор отправит вам код в **личные сообщения**.\n\n⏱ **Обычное время ожидания:** 1-5 минут\n\n👇 **Кнопка для запроса**",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Radmir МойДом | MP код")
                embed.timestamp = datetime.utcnow()
                await channel.send(embed=embed, view=TicketButtonView())
                print(f"✅ Панель отправлена в {channel.name}")

bot = TicketBot()

@bot.tree.command(name="panel", description="Отправить панель с кнопкой в канал")
@app_commands.default_permissions(administrator=True)
async def panel_command(interaction: discord.Interaction):
    channel = interaction.guild.get_channel(SOURCE_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)
        return
    embed = discord.Embed(title="🎮 ПОЛУЧЕНИЕ /MP КОДА", description="**🔹 Нужен код от /mp?**\n\nНажми на кнопку ниже — заявка будет отправлена организаторам.\nОрганизатор отправит вам код в **личные сообщения**.\n\n⏱ **Обычное время ожидания:** 1-5 минут\n\n👇 **Кнопка для запроса**", color=discord.Color.blue())
    embed.set_footer(text="Radmir МойДом | MP код")
    embed.timestamp = datetime.utcnow()
    await channel.send(embed=embed, view=TicketButtonView())
    await interaction.response.send_message(f"✅ Панель отправлена в {channel.mention}", ephemeral=True)

@bot.tree.command(name="setmod", description="Установить роль организаторов")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="Роль, которая будет получать уведомления о заявках")
async def setmod_command(interaction: discord.Interaction, role: discord.Role):
    global MODERATOR_ROLE_ID
    MODERATOR_ROLE_ID = role.id
    embed = discord.Embed(title="✅ Роль организаторов установлена", description=f"Теперь роль {role.mention} будет получать уведомления о новых заявках", color=discord.Color.green())
    embed.set_footer(text="Radmir МойДом")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ✅ НОВАЯ КОМАНДА /role - УСТАНОВКА РОЛИ ДЛЯ ВЫДАЧИ
@bot.tree.command(name="role", description="Установить роль для выдачи (например @Владелец семьи)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="Роль, которая будет выдаваться пользователю")
async def role_command(interaction: discord.Interaction, role: discord.Role):
    """Установка роли для выдачи"""
    
    # Сохраняем роль в JSON файл
    data = {}
    if os.path.exists('role_config.json'):
        with open('role_config.json', 'r') as f:
            data = json.load(f)
    
    data[str(interaction.guild_id)] = role.id
    
    with open('role_config.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    embed = discord.Embed(
        title="✅ Роль для выдачи установлена",
        description=f"При одобрении заявки будет выдаваться роль {role.mention}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Radmir МойДом")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    print(f"✅ Роль для выдачи установлена: {role.name} ({role.id})")

# ✅ КОМАНДА /test - ПРОВЕРКА РОЛЕЙ
@bot.tree.command(name="test", description="Проверить настройки ролей")
@app_commands.default_permissions(administrator=True)
async def test_command(interaction: discord.Interaction):
    """Проверка работы ролей"""
    
    moderator_role = interaction.guild.get_role(MODERATOR_ROLE_ID)
    mod_status = f"✅ {moderator_role.mention}" if moderator_role else "❌ Не настроена"
    
    # Проверяем роль для выдачи
    role_id = None
    if os.path.exists('role_config.json'):
        with open('role_config.json', 'r') as f:
            data = json.load(f)
            role_id = data.get(str(interaction.guild_id))
    
    reward_role = interaction.guild.get_role(role_id) if role_id else None
    reward_status = f"✅ {reward_role.mention}" if reward_role else "❌ Не настроена"
    
    embed = discord.Embed(
        title="📊 Статус настроек бота",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="👮 Роль организаторов", value=mod_status, inline=False)
    embed.add_field(name="🎁 Роль для выдачи", value=reward_status, inline=False)
    embed.add_field(name="📋 Канал заявок", value=f"<#{TICKET_REQUESTS_CHANNEL_ID}>", inline=False)
    embed.set_footer(text="Radmir МойДом")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Запуск бота
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Ошибка: Неверный токен бота!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")