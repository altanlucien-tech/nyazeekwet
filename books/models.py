from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os # ဖိုင်လမ်းကြောင်း စစ်ရန်အတွက် ထည့်သွင်းထားပါသည်
from .utils import upload_to_drive # Drive သို့ တင်ပေးမည့် function ကို ခေါ်ယူခြင်း

# Category ကို Book ရဲ့ အပေါ်သို့ ရွှေ့လိုက်သည် (ForeignKey Error မတက်စေရန်)
class Category(models.Model):
    name = models.CharField(max_length=100)
    is_manga = models.BooleanField(default=False) # Manga category လား၊ Book category လား ခွဲရန်
    is_for_shop = models.BooleanField(default=False) # Shop မှာပဲ သီးသန့်ပြချင်သော category ဖြစ်ပါက True ပေးရန်
    
    def __str__(self): 
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Author(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

# ၁။ စာအုပ်များသိမ်းဆည်းမည့် Model
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to='covers/')
    pdf_file = models.FileField(upload_to='protected_books/')
    description = models.TextField(blank=True)
    is_free = models.BooleanField(default=True) # True ဆိုရင် အလကား၊ False ဆိုရင် Paid စာအုပ်
    
    # Shop အတွက် အသစ်ထည့်ထားသော Field များ
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0) # စာအုပ်ဈေးနှုန်း
    is_for_sale = models.BooleanField(default=False) # Shop မှာ ရောင်းရန် ရှိ၊ မရှိ
    audio_file = models.FileField(upload_to='protected_audio/', blank=True, null=True) # Audiobook ပါလျှင်
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True) # Category နှင့် ချိတ်ဆက်မှု
    
    drive_file_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Drive File ID (PDF)")
    drive_audio_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Drive File ID (Audio)")
    drive_account_index = models.IntegerField(default=0, help_text="ဘယ်အကောင့်ကို သုံးမလဲ (0, 1, 2)")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Admin က SAVE နှိပ်လျှင် Drive ပေါ်သို့ အလိုအလျောက် ခွဲခြားတင်ပေးမည့် Logic"""
        # အရင်ဆုံး ဒေတာကို Database ထဲ သိမ်းလိုက်သည်
        super().save(*args, **kwargs)

        is_updated = False

        # ၁။ PDF ဖိုင်ရှိသော်လည်း Drive ID မရှိသေးပါက တင်မည်
        if self.pdf_file and not self.drive_file_id:
            try:
                # သင် Admin တွင် ရွေးထားသော drive_account_index အတိုင်း (0, 1 သို့မဟုတ် 2) တင်ပေးမည်
                file_id = upload_to_drive(self.pdf_file.path, f"{self.title}.pdf", self.drive_account_index)
                if file_id:
                    self.drive_file_id = file_id
                    is_updated = True
            except Exception as e:
                print(f"UPLOAD ERROR (PDF): {str(e)}")

        # ၂။ Audio ဖိုင်ရှိသော်လည်း Drive Audio ID မရှိသေးပါက တင်မည်
        if self.audio_file and not self.drive_audio_id:
            try:
                audio_id = upload_to_drive(self.audio_file.path, f"{self.title}_audio.mp3", self.drive_account_index)
                if audio_id:
                    self.drive_audio_id = audio_id
                    is_updated = True
            except Exception as e:
                print(f"UPLOAD ERROR (Audio): {str(e)}")

        # ID များ ရလာပါက Database တွင် ပြန်လည် Update လုပ်သည်
        if is_updated:
            super().save(*args, **kwargs)

# ၂။ Manga (ကာတွန်း) အတွက် Model
class Manga(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to='manga_covers/')
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

# ၃။ Manga Chapter များ
class Chapter(models.Model):
    manga = models.ForeignKey(Manga, related_name='chapters', on_delete=models.CASCADE)
    chapter_number = models.IntegerField()
    title = models.CharField(max_length=200, blank=True)
    pdf_file = models.FileField(upload_to='manga_chapters/')
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.manga.title} - Chapter {self.chapter_number}"

# ၄။ User ဝယ်ယူထားသော စာအုပ်များအား သိမ်းဆည်းရန်
class PurchasedBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book') # တစ်ယောက်တည်းက စာအုပ်တစ်အုပ်ကို နှစ်ခါဝယ်စရာမလိုရန်

    def __str__(self):
        return f"{self.user.username} bought {self.book.title}"

# ၅။ Premium Subscription များ
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    expiry_date = models.DateTimeField(null=True, blank=True)

    def has_access(self):
        return self.is_active and (self.expiry_date > timezone.now())

    def __str__(self):
        return f"{self.user.username} - {'Active' if self.has_access() else 'Expired'}"

# ၆။ ငွေလွှဲမှု မှတ်တမ်း (Manual Payment စစ်ဆေးရန်)
class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    screenshot = models.ImageField(upload_to='payments/')
    note = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Admin က အတည်ပြုလိုက်လျှင် PurchasedBook သို့ စာအုပ်ထည့်ပေးခြင်း (သို့) Subscription တိုးပေးခြင်း
        is_new_approval = False
        if self.pk:
            old_payment = Payment.objects.get(pk=self.pk)
            if not old_payment.is_approved and self.is_approved:
                is_new_approval = True
        
        super().save(*args, **kwargs)

        if is_new_approval:
            self.handle_approval()

    def handle_approval(self):
        # စာအုပ်ဝယ်ယူမှုလား၊ Subscription လား သိနိုင်ရန် logic များ
        # ဥပမာ - note ထဲတွင် book_id ပါလျှင် စာအုပ်ပေးမည်
        import re
        book_id_match = re.search(r'Purchase: (.*) -', self.note)
        
        # ၁။ အကယ်၍ စာအုပ်ဝယ်ယူခြင်းဖြစ်လျှင် (Book Title ပါလျှင်)
        if book_id_match:
            title = book_id_match.group(1).strip()
            target_book = Book.objects.filter(title=title).first()
            if target_book:
                PurchasedBook.objects.get_or_create(user=self.user, book=target_book)
        
        # ၂။ အကယ်၍ Subscription (VIP) တိုးခြင်းဖြစ်လျှင် (Book မပါလျှင်)
        else:
            sub, created = UserSubscription.objects.get_or_create(user=self.user)
            current_expiry = sub.expiry_date if sub.expiry_date and sub.expiry_date > timezone.now() else timezone.now()
            sub.is_active = True
            sub.expiry_date = current_expiry + timedelta(days=30)
            sub.save()

class History(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_history')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='view_history')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Histories"
        ordering = ['-viewed_at']
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} read {self.book.title}"

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_progress')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='user_progress')
    last_pdf_page = models.IntegerField(default=1)
    last_audio_position = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)