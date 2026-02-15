# GitHub yükleme — Son durum ve adımlar

**Repo:** https://github.com/MeetlyTR/mdm-engine  
**Remote:** `origin` → `https://github.com/MeetlyTR/mdm-engine.git`

---

## Son durum (özet)

- Yerelde birçok **değişiklik** var: güncellenmiş dosyalar (M), silinen dosyalar (D), yeni dosyalar (??).
- Bu değişiklikler henüz **commit edilmedi** ve **GitHub’a push edilmedi**.
- GitHub’a yüklemek için: önce **commit**, sonra **push** yapmanız yeterli. İsterseniz ardından **GitHub Release** ve/veya **PyPI** ekleyebilirsiniz.

---

## 1) Sadece GitHub’a kod yüklemek (commit + push)

### 1.1 Hangi dosyaların gideceğine karar verin

- **Hepsi:** Tüm değişiklikleri (güncel + yeni + silinen) commit edip push edebilirsiniz.
- **Kısmi:** Sadece belirli dosyaları stage edip commit edebilirsiniz.

### 1.2 Commit + push (PowerShell / CMD)

```powershell
cd c:\Users\tsgal\Desktop\ami-engine

# Tüm değişiklikleri stage et (yeni + değişen + silinen)
git add -A

# Durumu kontrol et
git status

# Commit (mesajı ihtiyaca göre değiştirin)
git commit -m "Dashboard iyileştirmeleri, review bundle, smoke test, README/REVIEW_BUNDLE güncellemeleri"

# GitHub'a push (varsayılan branch main ise)
git push origin main
```

Branch adınız farklıysa (örn. `master`):

```powershell
git push origin master
```

### 1.3 İlk kez push / yetki hatası

- **HTTPS** kullanıyorsanız: GitHub kullanıcı adı + **Personal Access Token (PAT)** ister (şifre artık kabul edilmiyor).
- **SSH** kullanıyorsanız: `git remote set-url origin git@github.com:MeetlyTR/mdm-engine.git` sonra `git push origin main`.

PAT: GitHub → Settings → Developer settings → Personal access tokens → Generate new token (repo yetkisi yeterli).

---

## 2) İsteğe bağlı: GitHub Release (tag + sürüm notu)

Kod zaten push edildiyse, sürüm etiketleyip release açmak için:

1. **Tag oluştur (yerelde):**
   ```powershell
   git tag -a v1.0.1 -m "Release v1.0.1"
   git push origin v1.0.1
   ```
2. **GitHub’da release oluştur:**  
   https://github.com/MeetlyTR/mdm-engine/releases/new  
   - Tag: `v1.0.1` seçin  
   - Title: `MDM v1.0.1`  
   - Açıklamaya CHANGELOG veya release notlarını yapıştırın  
   - “Publish release” tıklayın  

Detaylı liste: `docs/releases/RELEASE_CHECKLIST.md`

---

## 3) İsteğe bağlı: PyPI’ye yükleme

- **TestPyPI (önce denemek için):**  
  `docs/development/PYPI_RELEASE_GUIDE.md` ve `docs/development/RELEASE_COMMANDS.txt`  
  Özet: `python -m build` → `twine upload --repository testpypi dist/*`
- **Canlı PyPI:**  
  Aynı rehberde; `twine upload dist/*` (PyPI API token gerekir).

---

## Hızlı kontrol listesi

| Adım | Komut / işlem |
|------|----------------|
| 1. Stage | `git add -A` |
| 2. Commit | `git commit -m "..."` |
| 3. Push | `git push origin main` |
| 4. (Opsiyonel) Release | Tag + https://github.com/MeetlyTR/mdm-engine/releases/new |
| 5. (Opsiyonel) PyPI | `python -m build` → `twine upload ...` |

Bu dosya, “en son GitHub yükleme” için gerekli bilgileri tek yerde toplar. Silinen `GITHUB_YENIDEN_YUKLEME.md` yerine bu adımları kullanabilirsiniz.
