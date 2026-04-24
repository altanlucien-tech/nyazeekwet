import json
import os
import time
from pathlib import Path

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import url_has_allowed_host_and_scheme
from dotenv import load_dotenv
from django_ratelimit.decorators import ratelimit
from .models import Book, Payment, UserProgress, UserSubscription

# Model များအား Error မတက်စေရန် Try-Except ဖြင့် Import လုပ်ခြင်း
try:
    from .models import Category, Chapter, History, Manga, PurchasedBook

    CATEGORY_EXISTS = Category is not None
    HISTORY_EXISTS = History is not None
except ImportError:
    Category = None
    History = None
    Manga = None
    Chapter = None
    PurchasedBook = None
    CATEGORY_EXISTS = False
    HISTORY_EXISTS = False

load_dotenv()


def welcome_page(request):
    """ကြိုဆိုသည့် Page"""
    return render(request, "welcome.html")

@ratelimit(key='ip', rate='3/3m', method='POST', block=True)
def login_view(request):
    """Login ဝင်ရန် Logic"""
    if request.method == "POST":
        uname = request.POST.get("username")
        p1 = request.POST.get("password")
        user = authenticate(username=uname, password=p1)
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome back, {uname}!")
            return redirect("library")
        else:
            messages.error(request, "Username သို့မဟုတ် Password မှားယွင်းနေပါသည်။")
            
    if user:
        auth_login(request, user)
        # Redirect အတွက် လုံခြုံရေး စစ်ဆေးခြင်း
        next_url = request.GET.get('next')
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('library')
    return render(request, "login.html")


def register_view(request):
    """အကောင့်သစ်ဖွင့်ရန် Logic"""
    if request.method == "POST":
        uname = request.POST.get("username")
        uemail = request.POST.get("email")
        p1 = request.POST.get("password")
        p2 = request.POST.get("password_confirm")
        if p1 == p2:
            if User.objects.filter(username=uname).exists():
                messages.error(request, "ဤ Username မှာ အသုံးပြုပြီးသား ဖြစ်နေပါသည်။")
            else:
                User.objects.create_user(username=uname, email=uemail, password=p1)
                messages.success(
                    request, "အကောင့်ဖွင့်ခြင်း အောင်မြင်ပါသည်။ Login ပြန်ဝင်ပေးပါ။"
                )
                return redirect("login")
        else:
            messages.error(request, "Password နှစ်ခု မတူညီပါ။ ပြန်လည်စစ်ဆေးပါ။")
    return render(request, "register.html")


def library_view(request):
    """စာကြည့်တိုက် (Book/Manga) အားလုံးကြည့်ရန်"""
    category_slug = request.GET.get("category")
    search_query = request.GET.get("q")
    view_type = request.GET.get("type", "book")
    header_title = "Featured Books"

    is_premium = False
    purchased_ids = []

    if request.user.is_authenticated:
        sub = UserSubscription.objects.filter(user=request.user).first()
        if sub and sub.has_access():
            is_premium = True
        if PurchasedBook:
            purchased_ids = list(
                PurchasedBook.objects.filter(user=request.user).values_list(
                    "book_id", flat=True
                )
            )

    if view_type == "manga":
        categories = Category.objects.filter(is_manga=True) if CATEGORY_EXISTS else []
        all_items = Manga.objects.all().order_by("-id") if Manga else []
        header_title = "Manga Collection"
    else:
        categories = (
            Category.objects.filter(is_manga=False, is_for_shop=False)
            if CATEGORY_EXISTS
            else []
        )
        all_items = Book.objects.filter(is_for_sale=False).order_by("-id")
        header_title = "Book Store"

    if search_query:
        all_items = all_items.filter(
            Q(title__icontains=search_query) | Q(author__icontains=search_query)
        )
        header_title = f"Results for '{search_query}'"

    if category_slug and category_slug != "all" and CATEGORY_EXISTS:
        all_items = all_items.filter(category__name__iexact=category_slug)
        header_title = f"{category_slug.capitalize()} Items"

    paginator = Paginator(all_items, 12)
    page_number = request.GET.get("page")
    books = paginator.get_page(page_number)

    user_history = []
    if request.user.is_authenticated and HISTORY_EXISTS and History:
        try:
            user_history = list(
                History.objects.filter(user=request.user).values_list(
                    "book_id", flat=True
                )
            )
        except:
            user_history = []

    return render(
        request,
        "library.html",
        {
            "books": books,
            "is_premium": is_premium,
            "header_title": header_title,
            "user_history": user_history,
            "search_query": search_query,
            "categories": categories,
            "view_type": view_type,
            "purchased_ids": purchased_ids,
        },
    )


def shop_view(request):
    """ရောင်းရန်စာအုပ်များကြည့်ရန်"""
    category_slug = request.GET.get("category")
    search_query = request.GET.get("q")
    categories = Category.objects.filter(is_for_shop=True) if CATEGORY_EXISTS else []
    all_items = Book.objects.filter(is_for_sale=True).order_by("-id")

    purchased_ids = []
    is_premium = False
    if request.user.is_authenticated:
        if PurchasedBook:
            purchased_ids = list(
                PurchasedBook.objects.filter(user=request.user).values_list(
                    "book_id", flat=True
                )
            )
        sub = UserSubscription.objects.filter(user=request.user).first()
        if sub and sub.has_access():
            is_premium = True

    if category_slug == "My Books":
        if request.user.is_authenticated:
            all_items = all_items.filter(id__in=purchased_ids)
        else:
            return redirect("login")

    elif category_slug and category_slug != "all" and CATEGORY_EXISTS:
        all_items = all_items.filter(category__name__iexact=category_slug)

    if search_query:
        all_items = all_items.filter(
            Q(title__icontains=search_query) | Q(author__icontains=search_query)
        )

    paginator = Paginator(all_items, 12)
    page_number = request.GET.get("page")
    books = paginator.get_page(page_number)

    return render(
        request,
        "shop.html",
        {
            "books": books,
            "categories": categories,
            "purchased_ids": purchased_ids,
            "is_premium": is_premium,
            "search_query": search_query,
            "current_category": category_slug,
        },
    )


def show_ads_before_read(request):
    """ကြော်ငြာပြရန် View"""
    next_url = request.GET.get("next")
    if not next_url:
        return redirect("library")
    return render(request, "show_ads.html", {"next_url": next_url})


def read_book(request, book_id):
    """စာအုပ်ဖတ်ရန် Logic (Ad Redirect ပါဝင်သည်)"""
    book = get_object_or_404(Book, id=book_id)

    if request.user.is_authenticated and HISTORY_EXISTS and History:
        try:
            History.objects.update_or_create(
                user=request.user, book=book, defaults={"viewed_at": timezone.now()}
            )
        except Exception as e:
            print(f"History Save Error: {e}")

    can_access = False
    is_premium_user = False

    if request.user.is_authenticated:
        sub = UserSubscription.objects.filter(user=request.user).first()
        if sub and sub.has_access():
            is_premium_user = True
            can_access = True

        if not can_access and PurchasedBook:
            if PurchasedBook.objects.filter(user=request.user, book=book).exists():
                can_access = True

    if book.is_free:
        can_access = True

    if can_access:
        # Ad Logic: Free user ဖြစ်ပြီး ad မပြရသေးလျှင် Ad page သို့ ပို့မည်
        if book.is_free and not is_premium_user and not request.GET.get("ad_shown"):
            return redirect(f"/show-ads/?next=/read/{book.id}/?ad_shown=true")

        last_page = 1
        if request.user.is_authenticated:
            prog = UserProgress.objects.filter(user=request.user, book=book).first()
            if prog:
                last_page = prog.last_pdf_page

        try:
            response = redirect(f"{book.pdf_file.url}#page={last_page}")
            
            # 'inline' ထားမှသာ Browser ထဲမှာ တိုက်ရိုက်ပွင့်မည်
            response["Content-Disposition"] = (
                f'inline; filename="{book.title}.pdf"#page={last_page}'
            )
            return response
        except FileNotFoundError:
            raise Http404("စာအုပ်ဖိုင် ရှာမတွေ့ပါ။")
    else:
        if not request.user.is_authenticated:
            messages.info(
                request, "ဤစာအုပ်ကို ဖတ်ရှုရန် ကျေးဇူးပြု၍ Login အရင်ဝင်ပေးပါ။"
            )
            return redirect("login")
        else:
            messages.warning(
                request,
                "ဤစာအုပ်ကို ဖတ်ရှုရန် ဝယ်ယူရန် သို့မဟုတ် Premium ဖြစ်ရန် လိုအပ်ပါသည်။",
            )
            return redirect(f"/payment/?book_id={book.id}")


def read_chapter(request, chapter_id):
    """Manga Chapter ဖတ်ရန် Logic (Ad Redirect ပါဝင်သည်)"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    is_premium_user = False
    if request.user.is_authenticated:
        sub = UserSubscription.objects.filter(user=request.user).first()
        if sub and sub.has_access():
            is_premium_user = True

    if chapter.is_premium and not is_premium_user:
        messages.warning(request, "ဤအပိုင်းကိုဖတ်ရန် Premium ဝယ်ယူပါ။")
        return redirect("payment")

    # Ad Logic: Chapter က Premium မဟုတ်ဘဲ user ကလည်း Premium မဟုတ်လျှင်
    if (
        not chapter.is_premium
        and not is_premium_user
        and not request.GET.get("ad_shown")
    ):
        return redirect(f"/show-ads/?next=/manga/chapter/{chapter.id}/?ad_shown=true")

    return redirect(chapter.pdf_file.url)


def manga_chapters_api(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    chapters = list(
        manga.chapters.all().values("id", "chapter_number", "title", "is_premium")
    )
    return JsonResponse(chapters, safe=False)


def book_search_suggestions(request):
    """Search Suggestion API"""
    query = request.GET.get("term", "")
    source = request.GET.get("source", "")
    suggestions = []

    if query:
        books = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        )
        if source == "shop":
            books = books.filter(is_for_sale=True)
        elif source == "library":
            books = books.filter(is_for_sale=False)
        books = books[:5]
        for book in books:
            suggestions.append({"title": book.title, "author": str(book.author)})
    return JsonResponse(suggestions, safe=False)


def send_telegram_notification(user, note, photo_path):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    caption = f"🔔 New Payment Alert!\n👤 User: {user}\n📝 Note: {note}"
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            files = {"photo": photo}
            data = {"chat_id": chat_id, "caption": caption}
            requests.post(url, data=data, files=files, timeout=10)
    except Exception as e:
        print(f"Telegram Photo Error: {e}")


@login_required
def payment_page(request):
    book_id = request.GET.get("book_id")
    target_book = None
    if book_id:
        target_book = get_object_or_404(Book, id=book_id)

    if request.method == "POST":
        screenshot = request.FILES.get("screenshot")
        note = request.POST.get("note")
        payment = Payment.objects.create(
            user=request.user,
            screenshot=screenshot,
            note=f"Purchase: {target_book.title if target_book else 'Subscription'} - {note}",
        )

        if payment.screenshot:
            try:
                msg = f"Item: {target_book.title if target_book else 'Premium'}\nNote: {note}"
                send_telegram_notification(
                    request.user.username, msg, payment.screenshot.path
                )
            except:
                pass
        return render(request, "payment_success.html")
    return render(request, "payment.html", {"target_book": target_book})


@login_required
def listen_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    can_listen = False
    sub = UserSubscription.objects.filter(user=request.user).first()
    if (sub and sub.has_access()) or (
        PurchasedBook
        and PurchasedBook.objects.filter(user=request.user, book=book).exists()
    ):
        can_listen = True

    if can_listen:
        prog = UserProgress.objects.filter(user=request.user, book=book).first()
        audio_url = book.audio_file.url if book.audio_file else None
        return render(
            request,
            "listen_book.html",
            {"book": book, "audio_url": audio_url, "last_position": prog.last_audio_position if prog else 0},
        )
    messages.warning(
        request, "Audiobook နားထောင်ရန် ဝယ်ယူရန် သို့မဟုတ် Premium ဝယ်ယူပါ။"
    )
    return redirect(f"/payment/?book_id={book.id}")


@login_required
def audio_stream(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    can_stream = False
    sub = UserSubscription.objects.filter(user=request.user).first()
    if (sub and sub.has_access()) or (
        PurchasedBook
        and PurchasedBook.objects.filter(user=request.user, book=book).exists()
    ):
        can_stream = True

    if can_stream and book.audio_file:
        response = FileResponse(
            open(book.audio_file.path, "rb"), content_type="audio/mpeg"
        )
        response["Accept-Ranges"] = "bytes"
        return response
    raise Http404("Access Denied.")


@csrf_exempt
@login_required
def update_pdf_page(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            UserProgress.objects.update_or_create(
                user=request.user,
                book_id=data.get("book_id"),
                defaults={"last_pdf_page": data.get("page", 1)},
            )
            return JsonResponse({"status": "ok"})
        except:
            return JsonResponse({"error": "Invalid data"}, status=400)
    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
@login_required
def update_audio_position(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            UserProgress.objects.update_or_create(
                user=request.user,
                book_id=data.get("book_id"),
                defaults={"last_audio_position": data.get("position", 0)},
            )
            return JsonResponse({"status": "ok"})
        except:
            return JsonResponse({"error": "Invalid data"}, status=400)
    return JsonResponse({"error": "Invalid method"}, status=405)


def book_list_view(request):
    query = request.GET.get("q")
    books = (
        Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query))
        if query
        else Book.objects.all()
    )
    return render(request, "book_list.html", {"all_products": books})
