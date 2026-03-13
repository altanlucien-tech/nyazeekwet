from django.contrib import admin
from .models import Book, Payment, UserSubscription, Category, Manga, Chapter, PurchasedBook, History, UserProgress

# Manga တစ်ခုအောက်တွင် Chapter များကို တစ်ခါတည်း ထည့်သွင်းနိုင်ရန် Inline သုံးထားခြင်း
class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1  # အသစ်ထည့်ရန် အကွက်အလွတ် တစ်ကွက် အမြဲပြနေမည်

@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    # 'created_at' မရှိသောကြောင့် list_display မှ ဖယ်ရှားထားပါသည်
    list_display = ('title', 'author', 'category')
    search_fields = ('title', 'author')
    list_filter = ('category',)
    inlines = [ChapterInline]

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('manga', 'chapter_number', 'title', 'is_premium')
    list_filter = ('is_premium', 'manga')
    search_fields = ('title', 'manga__title')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    # Shop နှင့်ဆိုင်သော field များပါ ထည့်သွင်းပြသပေးထားပါသည်
    list_display = ('title', 'author', 'is_free', 'is_for_sale', 'price')
    search_fields = ('title', 'author')
    list_filter = ('is_free', 'is_for_sale', 'category')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # 'status' အစား 'is_approved' သို့ ပြောင်းလဲပြင်ဆင်ထားပါသည်
    list_display = ('user', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    list_editable = ('is_approved',) 
    search_fields = ('user__username', 'note')

# Category Admin တွင် Manga လား၊ Book လား၊ Shop Category လား ခွဲခြားမြင်နိုင်ရန် ပြင်ဆင်ခြင်း
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_manga', 'is_for_shop')
    list_filter = ('is_manga', 'is_for_shop')

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'expiry_date')
    list_filter = ('is_active',)

@admin.register(PurchasedBook)
class PurchasedBookAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'purchased_at')
    search_fields = ('user__username', 'book__title')

@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'viewed_at')

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'last_pdf_page', 'updated_at')