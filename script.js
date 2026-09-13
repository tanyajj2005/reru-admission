/* ========================================
   Faculty of Information Technology
   script.js — All interactive features
   ======================================== */

document.addEventListener('DOMContentLoaded', function () {

  // ========================================
  // 1. Mobile Hamburger Menu
  // ========================================
  const hamburger = document.getElementById('hamburger');
  const navMenu = document.getElementById('navMenu');
  const mobileOverlay = document.getElementById('mobileOverlay');

  function openMenu() {
    hamburger.classList.add('active');
    navMenu.classList.add('active');
    mobileOverlay.classList.add('active');
    mobileOverlay.style.display = 'block';
    document.body.style.overflow = 'hidden';
    // Trigger reflow for transition
    requestAnimationFrame(function () {
      mobileOverlay.classList.add('active');
    });
  }

  function closeMenu() {
    hamburger.classList.remove('active');
    navMenu.classList.remove('active');
    mobileOverlay.classList.remove('active');
    document.body.style.overflow = '';
    setTimeout(function () {
      if (!mobileOverlay.classList.contains('active')) {
        mobileOverlay.style.display = 'none';
      }
    }, 300);
  }

  if (hamburger) {
    hamburger.addEventListener('click', function () {
      if (navMenu.classList.contains('active')) {
        closeMenu();
      } else {
        openMenu();
      }
    });
  }

  if (mobileOverlay) {
    mobileOverlay.addEventListener('click', closeMenu);
  }

  // Close menu when a nav link is clicked
  var navLinks = navMenu ? navMenu.querySelectorAll('a') : [];
  navLinks.forEach(function (link) {
    link.addEventListener('click', closeMenu);
  });

  // ========================================
  // 2. Smooth Scroll
  // ========================================
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var targetId = this.getAttribute('href');
      if (targetId === '#') return;
      var target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        var headerHeight = document.querySelector('.header') ? document.querySelector('.header').offsetHeight : 0;
        var announceBar = document.querySelector('.announcement-bar');
        var announceHeight = announceBar ? announceBar.offsetHeight : 0;
        var top = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });

  // ========================================
  // 3. Sticky Navbar & Scrolled State
  // ========================================
  var header = document.querySelector('.header');

  function handleScroll() {
    if (!header) return;
    if (window.scrollY > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', handleScroll);
  handleScroll();

  // ========================================
  // 4. Active Navigation Highlight
  // ========================================
  var sections = document.querySelectorAll('section[id]');
  var allNavLinks = document.querySelectorAll('.nav-menu a[href^="#"]');

  function updateActiveNav() {
    var scrollPos = window.scrollY + 200;
    sections.forEach(function (section) {
      var top = section.offsetTop;
      var height = section.offsetHeight;
      var id = section.getAttribute('id');
      if (scrollPos >= top && scrollPos < top + height) {
        allNavLinks.forEach(function (link) {
          link.classList.remove('active');
          if (link.getAttribute('href') === '#' + id) {
            link.classList.add('active');
          }
        });
      }
    });
  }

  window.addEventListener('scroll', updateActiveNav);
  updateActiveNav();

  // ========================================
  // 5. Scroll Reveal Animation
  // ========================================
  var revealElements = document.querySelectorAll('.reveal');

  function handleReveal() {
    revealElements.forEach(function (el) {
      var top = el.getBoundingClientRect().top;
      var trigger = window.innerHeight * 0.88;
      if (top < trigger) {
        el.classList.add('revealed');
      }
    });
  }

  window.addEventListener('scroll', handleReveal);
  handleReveal();

  // ========================================
  // 6. Animated Statistics Counter
  // ========================================
  var statNumbers = document.querySelectorAll('.stat-number');
  var statsAnimated = false;
  var statsSection = document.getElementById('statistics');

  function animateCounters() {
    if (statsAnimated || !statsSection) return;
    var top = statsSection.getBoundingClientRect().top;
    if (top < window.innerHeight * 0.85) {
      statsAnimated = true;
      statNumbers.forEach(function (el) {
        var target = parseInt(el.getAttribute('data-target'), 10);
        var suffix = el.getAttribute('data-suffix') || '';
        var duration = 2000;
        var startTime = null;

        function step(timestamp) {
          if (!startTime) startTime = timestamp;
          var progress = Math.min((timestamp - startTime) / duration, 1);
          // Ease out cubic
          var eased = 1 - Math.pow(1 - progress, 3);
          var current = Math.floor(eased * target);
          el.textContent = current.toLocaleString() + suffix;
          if (progress < 1) {
            requestAnimationFrame(step);
          } else {
            el.textContent = target.toLocaleString() + suffix;
          }
        }

        requestAnimationFrame(step);
      });
    }
  }

  window.addEventListener('scroll', animateCounters);
  animateCounters();

  // ========================================
  // 7. Admission Countdown
  // ========================================
  var countdownEl = document.getElementById('countdown');
  var countdownExpired = document.getElementById('countdownExpired');

  // Target date: Dec 31, 2026
  var targetDate = new Date('2026-12-31T23:59:59').getTime();

  function updateCountdown() {
    if (!countdownEl) return;
    var now = new Date().getTime();
    var diff = targetDate - now;

    if (diff <= 0) {
      countdownEl.style.display = 'none';
      if (countdownExpired) countdownExpired.style.display = 'block';
      return;
    }

    var days = Math.floor(diff / (1000 * 60 * 60 * 24));
    var hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    var minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    var seconds = Math.floor((diff % (1000 * 60)) / 1000);

    var daysEl = document.getElementById('cdDays');
    var hoursEl = document.getElementById('cdHours');
    var minsEl = document.getElementById('cdMins');
    var secsEl = document.getElementById('cdSecs');

    if (daysEl) daysEl.textContent = days;
    if (hoursEl) hoursEl.textContent = hours.toString().padStart(2, '0');
    if (minsEl) minsEl.textContent = minutes.toString().padStart(2, '0');
    if (secsEl) secsEl.textContent = seconds.toString().padStart(2, '0');
  }

  updateCountdown();
  setInterval(updateCountdown, 1000);

  // ========================================
  // 8. FAQ Accordion
  // ========================================
  var faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach(function (item) {
    var question = item.querySelector('.faq-question');
    var answer = item.querySelector('.faq-answer');

    question.addEventListener('click', function () {
      var isActive = item.classList.contains('active');

      // Close all
      faqItems.forEach(function (i) {
        i.classList.remove('active');
        var a = i.querySelector('.faq-answer');
        if (a) a.style.maxHeight = null;
      });

      // Open clicked if was closed
      if (!isActive) {
        item.classList.add('active');
        if (answer) {
          answer.style.maxHeight = answer.scrollHeight + 'px';
        }
      }
    });

    // Keyboard support
    question.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        question.click();
      }
    });
  });

  // ========================================
  // 9. News Search
  // ========================================
  var newsSearch = document.getElementById('newsSearch');
  var newsCards = document.querySelectorAll('.news-card');

  function filterNews() {
    var query = newsSearch ? newsSearch.value.toLowerCase().trim() : '';
    var activeCategory = document.querySelector('.filter-btn.active');
    var category = activeCategory ? activeCategory.getAttribute('data-category') : 'all';

    newsCards.forEach(function (card) {
      var title = card.getAttribute('data-title') || '';
      var cardCategory = card.getAttribute('data-category') || '';
      var matchesSearch = title.toLowerCase().includes(query);
      var matchesCategory = category === 'all' || cardCategory === category;

      if (matchesSearch && matchesCategory) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  }

  if (newsSearch) {
    newsSearch.addEventListener('input', filterNews);
  }

  // ========================================
  // 10. News Category Filter
  // ========================================
  var filterBtns = document.querySelectorAll('.filter-btn');

  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      filterBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      filterNews();
    });
  });

  // ========================================
  // 11. Back To Top Button
  // ========================================
  var backToTop = document.getElementById('backToTop');

  function handleBackToTop() {
    if (!backToTop) return;
    if (window.scrollY > 400) {
      backToTop.classList.add('visible');
    } else {
      backToTop.classList.remove('visible');
    }
  }

  window.addEventListener('scroll', handleBackToTop);
  handleBackToTop();

  if (backToTop) {
    backToTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ========================================
  // 13. Form Validation
  // ========================================
  var contactForm = document.getElementById('contactForm');
  var formSuccess = document.getElementById('formSuccess');

  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var isValid = true;

      // Clear previous errors
      contactForm.querySelectorAll('.form-group').forEach(function (group) {
        group.classList.remove('error');
      });

      // Validate name
      var nameField = document.getElementById('formName');
      if (nameField && nameField.value.trim() === '') {
        nameField.closest('.form-group').classList.add('error');
        isValid = false;
      }

      // Validate email
      var emailField = document.getElementById('formEmail');
      if (emailField) {
        var emailVal = emailField.value.trim();
        var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (emailVal === '' || !emailPattern.test(emailVal)) {
          emailField.closest('.form-group').classList.add('error');
          isValid = false;
        }
      }

      // Validate subject
      var subjectField = document.getElementById('formSubject');
      if (subjectField && subjectField.value.trim() === '') {
        subjectField.closest('.form-group').classList.add('error');
        isValid = false;
      }

      // Validate message
      var messageField = document.getElementById('formMessage');
      if (messageField && messageField.value.trim() === '') {
        messageField.closest('.form-group').classList.add('error');
        isValid = false;
      }

      if (isValid) {
        contactForm.style.display = 'none';
        if (formSuccess) formSuccess.classList.add('active');

        // Reset form after 3 seconds
        setTimeout(function () {
          contactForm.reset();
          contactForm.style.display = 'block';
          if (formSuccess) formSuccess.classList.remove('active');
        }, 4000);
      }
    });
  }

  // ========================================
  // 14. Scroll to Admission on CTA clicks
  // ========================================
  // Handled by smooth scroll (#admission)

  // ========================================
  // 15. 3 Major Cards Interactive Animation & Hover
  // ========================================
  var majorCards = document.querySelectorAll('.major-card');
  majorCards.forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      var logo = this.querySelector('.major-logo-img, .official-logo-placeholder');
      if (logo) {
        logo.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
      }
    });

    var btn = card.querySelector('.major-btn');
    if (btn) {
      btn.addEventListener('click', function (e) {
        // Smooth transition / feedback
        var majorType = card.getAttribute('data-major');
        if (majorType) {
          sessionStorage.setItem('preferred_dept', majorType);
        }
      });
    }
  });

  // ========================================
  // Stagger reveal delays
  // ========================================
  // ========================================
  // 16. Load & Render News & Activities
  // ========================================
  const DEFAULT_NEWS_ITEMS = [
    {
      id: 'act_001',
      title: 'ขับเคลื่อน IT RERU สู่ "องค์กรสมรรถนะสูง" คณะเทคโนโลยีสารสนเทศ มหาวิทยาลัยราชภัฏร้อยเอ็ด',
      description: 'คณะเทคโนโลยีสารสนเทศ มหาวิทยาลัยราชภัฏร้อยเอ็ด จัดโครงการขับเคลื่อนองค์กรสู่สมรรถนะสูง พัฒนากระบวนการทำงานและศักยภาพบุคลากร',
      image_url: 'image/เทคโน.jpg',
      published_date: '2026-03-05',
      source_page: 'It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด',
      source_url: 'https://www.facebook.com/ITRERU',
      category: 'FEATURED_ACTIVITY'
    },
    {
      id: 'act_002',
      title: 'โครงการอบรมเชิงปฏิบัติการพัฒนาทักษะดิจิทัลและปัญญาประดิษฐ์ (AI)',
      description: 'เสริมสร้างทักษะ AI และเทคโนโลยีดิจิทัลยุคใหม่ให้กับนักศึกษาและผู้สนใจ เพื่อเตรียมความพร้อมสู่สายงานเทคโนโลยีสารสนเทศ',
      image_url: 'images/staff/66d683a6_stf_0e931a02016a.jpg',
      published_date: '2026-03-01',
      source_page: 'สื่อสารองค์กร คณะเทคโนโลยีสารสนเทศ ม.ราชภัฏร้อยเอ็ด',
      source_url: 'https://www.facebook.com/profile.php?id=61576262831080',
      category: 'FEATURED_ACTIVITY'
    },
    {
      id: 'act_003',
      title: 'พิธีไหว้ครูและมอบทุนการศึกษาประจำปีการศึกษา คณะเทคโนโลยีสารสนเทศ',
      description: 'กิจกรรมสืบสานประเพณีไหว้ครู พร้อมมอบทุนการศึกษาแก่นักศึกษาที่มีผลการเรียนดีเยี่ยมและมีความประพฤติดี',
      image_url: 'images/staff/5fb2d150_stf_7702b6342428.jpg',
      published_date: '2026-02-20',
      source_page: 'It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด',
      source_url: 'https://www.facebook.com/ITRERU',
      category: 'FEATURED_ACTIVITY'
    },
    {
      id: 'news_001',
      title: 'ประกาศการเปิดรับสมัครนักศึกษาใหม่ ประจำปีการศึกษา 2569 (รอบที่ 2 โควตา)',
      description: 'คณะเทคโนโลยีสารสนเทศ มหาวิทยาลัยราชภัฏร้อยเอ็ด เปิดรับสมัครนักศึกษาใหม่ระดับปริญญาตรี ใน 3 สาขาวิชาเด่น CS, IT และ MSI',
      image_url: 'images/staff/139477d4_stf_25c871423d3a.jpg',
      published_date: '2026-03-10',
      source_page: 'It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด',
      source_url: 'https://www.facebook.com/ITRERU',
      category: 'LATEST_NEWS'
    },
    {
      id: 'news_002',
      title: 'นักศึกษาคณะเทคโนโลยีสารสนเทศ คว้ารางวัลการแข่งขันทักษะคอมพิวเตอร์ระดับภูมิภาค',
      description: 'ขอแสดงความยินดีกับทีมตัวแทนนักศึกษาที่ได้รับรางวัลจากการแข่งขันพัฒนาซอฟต์แวร์และนวัตกรรม AI',
      image_url: 'images/staff/96e4fdbf_stf_f3be88e004d5.jpg',
      published_date: '2026-03-08',
      source_page: 'สื่อสารองค์กร คณะเทคโนโลยีสารสนเทศ ม.ราชภัฏร้อยเอ็ด',
      source_url: 'https://www.facebook.com/profile.php?id=61576262831080',
      category: 'LATEST_NEWS'
    },
    {
      id: 'news_003',
      title: 'ขอเชิญชวนเข้าร่วมงานสัปดาห์วิทยาศาสตร์และเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด',
      description: 'พบกับนิทรรศการนวัตกรรม AI, การประกวดโครงงานซอฟต์แวร์ และกิจกรรม Workshop การเขียนโปรแกรมสำหรับผู้สนใจ',
      image_url: 'image/เทคโน.jpg',
      published_date: '2026-03-02',
      source_page: 'It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด',
      source_url: 'https://www.facebook.com/ITRERU',
      category: 'LATEST_NEWS'
    }
  ];

  async function loadNewsAndActivities() {
    const actContainer = document.getElementById('activities-container');
    const newsContainer = document.getElementById('news-container');

    let items = [];
    try {
      const apiUrl = (window.location.protocol === 'file:') ? 'http://localhost:8000/api/news-activities' : '/api/news-activities';
      const res = await fetch(apiUrl);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.items && data.items.length > 0) {
          items = data.items;
        }
      }
    } catch (e) {
      console.warn('Using default items fallback:', e);
    }

    if (!items || items.length === 0) {
      items = DEFAULT_NEWS_ITEMS;
    }

    const activities = items.filter(item => item.category === 'activity' || item.category === 'FEATURED_ACTIVITY');
    const news = items.filter(item => item.category === 'news' || item.category === 'LATEST_NEWS');

    // Render Activities
    if (actContainer) {
      if (activities.length === 0) {
        actContainer.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--gray-500);">ยังไม่มีข้อมูลกิจกรรม</div>';
      } else {
        actContainer.innerHTML = activities.map(item => createPostCardHTML(item, 'อ่านเพิ่มเติม')).join('');
      }
    }

    // Render News
    if (newsContainer) {
      if (news.length === 0) {
        newsContainer.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--gray-500);">ยังไม่มีข่าวสารล่าสุด</div>';
      } else {
        newsContainer.innerHTML = news.map(item => createPostCardHTML(item, 'อ่านข่าว')).join('');
      }
    }
  }

  function createPostCardHTML(item, btnLabel) {
    const fallbackImg = 'image/เทคโน.jpg';
    const imgUrl = item.image_url ? item.image_url : (item.image ? item.image : fallbackImg);
    const sourcePage = item.source_page || item.sourcePage || 'It RERU คณะเทคโนโลยีสารสนเทศ มรภ.ร้อยเอ็ด';
    const sourceUrl = item.source_url || item.sourceUrl || 'https://www.facebook.com/ITRERU';
    const dateFormatted = item.published_date || item.publishedDate || '';
    const isAct = item.category === 'activity' || item.category === 'FEATURED_ACTIVITY';
    const badgeText = isAct ? '🌟 กิจกรรมเด่น' : '📰 ข่าวสาร';

    return `
      <div class="post-card reveal active">
        <div class="post-img-wrapper">
          <img src="${imgUrl}" alt="${item.title}" loading="lazy" onerror="this.src='${fallbackImg}'">
          <span class="post-badge">${badgeText}</span>
        </div>
        <div class="post-body">
          <div class="post-date">📅 ${dateFormatted}</div>
          <h3 class="post-title" title="${item.title}">${item.title}</h3>
          <p class="post-desc">${item.description || ''}</p>
          <div class="post-footer">
            <div class="post-source">
              <span>ที่มา:</span>
              <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer">${sourcePage}</a>
            </div>
            <a href="${sourceUrl}" target="_blank" rel="noopener noreferrer" class="post-btn">
              ${btnLabel} →
            </a>
          </div>
        </div>
      </div>
    `;
  }

  window.loadNewsAndActivities = loadNewsAndActivities;
  loadNewsAndActivities();

  // ========================================
  // 11. Student Application Form Modal System
  // ========================================
  const modal = document.getElementById('applicationModal');
  const applyBtn = document.getElementById('applyCourseBtn');
  const heroBtn = document.getElementById('heroApplyBtn');
  const closeBtn = document.getElementById('closeAppModalBtn');
  
  const btnNext = document.getElementById('btnNextStep');
  const btnPrev = document.getElementById('btnPrevStep');
  const btnEdit = document.getElementById('btnEditStep');
  const btnSubmit = document.getElementById('btnSubmitApp');
  const btnCloseSuccess = document.getElementById('btnCloseSuccess');

  let currentStep = 1;
  const maxSteps = 5;

  // File Store
  let uploadedFiles = {
    photo: null,
    transcript: null,
    other: null
  };

  function openApplicationModal(e) {
    if (e) e.preventDefault();
    if (modal) {
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
      goToStep(1);
    }
  }

  function closeApplicationModal() {
    if (modal) {
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }

  if (applyBtn) applyBtn.addEventListener('click', openApplicationModal);
  if (heroBtn) heroBtn.addEventListener('click', openApplicationModal);
  if (closeBtn) closeBtn.addEventListener('click', closeApplicationModal);
  if (btnCloseSuccess) btnCloseSuccess.addEventListener('click', closeApplicationModal);

  // Close modal on background click
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        closeApplicationModal();
      }
    });
  }

  // File Inputs Event Listeners
  setupFileInput('filePhoto', 'previewPhoto', 'photo');
  setupFileInput('fileTranscript', 'previewTranscript', 'transcript');
  setupFileInput('fileOther', 'previewOther', 'other');

  function setupFileInput(inputId, previewId, fileKey) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (!input || !preview) return;

    input.addEventListener('change', function() {
      if (input.files && input.files[0]) {
        const file = input.files[0];
        if (file.size > 5 * 1024 * 1024) {
          alert('ขนาดไฟล์ต้องไม่เกิน 5MB');
          input.value = '';
          return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
          uploadedFiles[fileKey] = {
            name: file.name,
            size: file.size,
            mime: file.type || 'application/octet-stream',
            data: e.target.result,
            type: fileKey
          };
          preview.textContent = `✅ เลือกแล้ว: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
          preview.classList.add('has-file');
        };
        reader.readAsDataURL(file);
      } else {
        uploadedFiles[fileKey] = null;
        preview.textContent = 'ยังไม่ได้เลือกไฟล์';
        preview.classList.remove('has-file');
      }
    });
  }

  // Step Navigation logic
  function goToStep(step) {
    currentStep = step;

    // Update Step Contents
    for (let i = 1; i <= 6; i++) {
      const content = document.getElementById(`appStep${i}`);
      if (content) {
        if (i === currentStep) {
          content.classList.add('active');
        } else {
          content.classList.remove('active');
        }
      }
    }

    // Update Step Indicators
    const indicator = document.getElementById('appStepIndicator');
    if (indicator) {
      if (currentStep === 6) {
        indicator.style.display = 'none';
      } else {
        indicator.style.display = 'flex';
        document.querySelectorAll('#appStepIndicator .step-item').forEach(item => {
          const s = parseInt(item.dataset.step, 10);
          item.classList.remove('active', 'completed');
          if (s === currentStep) {
            item.classList.add('active');
          } else if (s < currentStep) {
            item.classList.add('completed');
          }
        });
      }
    }

    // Buttons Visibility Control
    if (currentStep === 1) {
      btnPrev.style.display = 'none';
      btnEdit.style.display = 'none';
      btnNext.style.display = 'inline-block';
      btnSubmit.style.display = 'none';
      btnCloseSuccess.style.display = 'none';
    } else if (currentStep > 1 && currentStep < 5) {
      btnPrev.style.display = 'inline-block';
      btnEdit.style.display = 'none';
      btnNext.style.display = 'inline-block';
      btnSubmit.style.display = 'none';
      btnCloseSuccess.style.display = 'none';
    } else if (currentStep === 5) {
      btnPrev.style.display = 'none';
      btnEdit.style.display = 'inline-block';
      btnNext.style.display = 'none';
      btnSubmit.style.display = 'inline-block';
      btnCloseSuccess.style.display = 'none';
      populateSummary();
    } else if (currentStep === 6) {
      btnPrev.style.display = 'none';
      btnEdit.style.display = 'none';
      btnNext.style.display = 'none';
      btnSubmit.style.display = 'none';
      btnCloseSuccess.style.display = 'inline-block';
    }
  }

  // Next Step with Strict Validation
  if (btnNext) {
    btnNext.addEventListener('click', function() {
      if (validateStep(currentStep)) {
        goToStep(currentStep + 1);
      }
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', function() {
      if (currentStep > 1) {
        goToStep(currentStep - 1);
      }
    });
  }

  if (btnEdit) {
    btnEdit.addEventListener('click', function() {
      goToStep(1);
    });
  }

  // Validation function for required fields (*)
  function validateStep(step) {
    if (step === 1) {
      const firstName = document.getElementById('apFirstName').value.trim();
      const lastName = document.getElementById('apLastName').value.trim();
      const dob = document.getElementById('apDob').value.trim();
      const nationalId = document.getElementById('apNationalId').value.trim();
      const phone = document.getElementById('apPhone').value.trim();
      const address = document.getElementById('apAddress').value.trim();
      const province = document.getElementById('apProvince').value.trim();

      if (!firstName) { alert('กรุณากรอกชื่อ'); document.getElementById('apFirstName').focus(); return false; }
      if (!lastName) { alert('กรุณากรอกนามสกุล'); document.getElementById('apLastName').focus(); return false; }
      if (!dob) { alert('กรุณากรอกวัน/เดือน/ปีเกิด'); document.getElementById('apDob').focus(); return false; }
      if (!nationalId || nationalId.length !== 13 || !/^\d+$/.test(nationalId)) {
        alert('กรุณากรอกเลขบัตรประชาชนให้ครบ 13 หลัก');
        document.getElementById('apNationalId').focus();
        return false;
      }
      if (!phone) { alert('กรุณากรอกเบอร์โทรศัพท์'); document.getElementById('apPhone').focus(); return false; }
      if (!address) { alert('กรุณากรอกที่อยู่ปัจจุบัน'); document.getElementById('apAddress').focus(); return false; }
      if (!province) { alert('กรุณากรอกจังหวัด'); document.getElementById('apProvince').focus(); return false; }
    } else if (step === 2) {
      const school = document.getElementById('apSchool').value.trim();
      const gpax = parseFloat(document.getElementById('apGpax').value);

      if (!school) { alert('กรุณากรอกชื่อโรงเรียนเดิม'); document.getElementById('apSchool').focus(); return false; }
      if (isNaN(gpax) || gpax <= 0 || gpax > 4.0) {
        alert('กรุณากรอกเกรดเฉลี่ยสะสม (GPAX) ให้ถูกต้อง (0.00 - 4.00)');
        document.getElementById('apGpax').focus();
        return false;
      }
    } else if (step === 3) {
      const prog = document.getElementById('apProgram').value;
      if (!prog) { alert('กรุณาเลือกสาขาวิชา/หลักสูตรที่ต้องการสมัคร'); document.getElementById('apProgram').focus(); return false; }
    }

    return true;
  }

  // Populate Summary Step
  function populateSummary() {
    const prefixEl = document.querySelector('input[name="apPrefix"]:checked');
    const prefix = prefixEl ? prefixEl.value : 'นาย';
    const firstName = document.getElementById('apFirstName').value.trim();
    const lastName = document.getElementById('apLastName').value.trim();
    const fullName = `${prefix}${firstName} ${lastName}`;
    const nickname = document.getElementById('apNickname').value.trim() || '-';
    const dob = document.getElementById('apDob').value;
    const nationalId = document.getElementById('apNationalId').value.trim();
    const phone = document.getElementById('apPhone').value.trim();
    const email = document.getElementById('apEmail').value.trim() || '-';
    
    const address = document.getElementById('apAddress').value.trim();
    const subdistrict = document.getElementById('apSubdistrict').value.trim();
    const district = document.getElementById('apDistrict').value.trim();
    const province = document.getElementById('apProvince').value.trim();
    const zipcode = document.getElementById('apZipcode').value.trim();
    const fullAddr = `${address} ${subdistrict ? 'ต.'+subdistrict : ''} ${district ? 'อ.'+district : ''} จ.${province} ${zipcode}`;

    const school = document.getElementById('apSchool').value.trim();
    const degreeLevel = document.getElementById('apDegreeLevel').value;
    const gpax = parseFloat(document.getElementById('apGpax').value).toFixed(2);
    const gradYear = document.getElementById('apGradYear').value.trim() || '-';

    const progCode = document.getElementById('apProgram').value;
    const progMap = {
      'CS': 'วิทยาการคอมพิวเตอร์ (Computer Science)',
      'IT': 'เทคโนโลยีสารสนเทศ (Information Technology)',
      'MSI': 'วิทยาการมัลติมีเดียปัญญาประดิษฐ์ (Multimedia & AI)'
    };
    const programName = progMap[progCode] || progCode;
    const targetDegree = document.getElementById('apTargetDegree').value;
    const round = document.getElementById('apRound').value;

    document.getElementById('sumFullName').textContent = fullName;
    document.getElementById('sumNickname').textContent = nickname;
    document.getElementById('sumDob').textContent = dob;
    document.getElementById('sumNationalId').textContent = nationalId;
    document.getElementById('sumPhone').textContent = phone;
    document.getElementById('sumEmail').textContent = email;
    document.getElementById('sumAddress').textContent = fullAddr;

    document.getElementById('sumSchool').textContent = school;
    document.getElementById('sumDegreeLevel').textContent = degreeLevel;
    document.getElementById('sumGpax').textContent = gpax;
    document.getElementById('sumGradYear').textContent = gradYear;

    document.getElementById('sumProgram').textContent = programName;
    document.getElementById('sumTargetDegree').textContent = targetDegree;
    document.getElementById('sumRound').textContent = round;

    document.getElementById('sumFilePhoto').textContent = uploadedFiles.photo ? uploadedFiles.photo.name : 'ไม่ได้แนบ';
    document.getElementById('sumFileTranscript').textContent = uploadedFiles.transcript ? uploadedFiles.transcript.name : 'ไม่ได้แนบ';
    document.getElementById('sumFileOther').textContent = uploadedFiles.other ? uploadedFiles.other.name : 'ไม่ได้แนบ';
  }

  // Submit Application
  if (btnSubmit) {
    btnSubmit.addEventListener('click', async function() {
      btnSubmit.disabled = true;
      btnSubmit.textContent = '⏳ กำลังส่งข้อมูล...';

      const prefixEl = document.querySelector('input[name="apPrefix"]:checked');
      const prefix = prefixEl ? prefixEl.value : 'นาย';
      const firstName = document.getElementById('apFirstName').value.trim();
      const lastName = document.getElementById('apLastName').value.trim();

      const docsList = [];
      if (uploadedFiles.photo) docsList.push(uploadedFiles.photo);
      if (uploadedFiles.transcript) docsList.push(uploadedFiles.transcript);
      if (uploadedFiles.other) docsList.push(uploadedFiles.other);

      const payload = {
        prefix: prefix,
        first_name: firstName,
        last_name: lastName,
        full_name: `${prefix}${firstName} ${lastName}`,
        nickname: document.getElementById('apNickname').value.trim(),
        dob: document.getElementById('apDob').value,
        national_id: document.getElementById('apNationalId').value.trim(),
        phone: document.getElementById('apPhone').value.trim(),
        email: document.getElementById('apEmail').value.trim(),
        address: document.getElementById('apAddress').value.trim(),
        subdistrict: document.getElementById('apSubdistrict').value.trim(),
        district: document.getElementById('apDistrict').value.trim(),
        province: document.getElementById('apProvince').value.trim(),
        zipcode: document.getElementById('apZipcode').value.trim(),
        school_name: document.getElementById('apSchool').value.trim(),
        degree_level: document.getElementById('apDegreeLevel').value,
        gpax: parseFloat(document.getElementById('apGpax').value),
        grad_year: document.getElementById('apGradYear').value.trim(),
        program_code: document.getElementById('apProgram').value,
        admission_round: document.getElementById('apRound').value,
        documents: docsList
      };

      try {
        const apiUrl = (window.location.protocol === 'file:') ? 'http://localhost:8000/api/applications/submit' : '/api/applications/submit';
        const res = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || 'เกิดข้อผิดพลาดในการบันทึกใบสมัคร');
        }

        // Show Success Step
        document.getElementById('resAppId').textContent = data.application_id || 'RERU-AD-000001';
        document.getElementById('resFullName').textContent = payload.full_name;
        document.getElementById('resProgram').textContent = data.application ? data.application.program_name : payload.program_code;
        document.getElementById('resDate').textContent = new Date().toLocaleDateString('th-TH');
        document.getElementById('resStatus').textContent = '⏳ รอตรวจสอบ';

        goToStep(6);

      } catch (err) {
        alert('เกิดข้อผิดพลาด: ' + err.message);
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.textContent = '✅ ยืนยันส่งใบสมัคร';
      }
    });
  }

});
