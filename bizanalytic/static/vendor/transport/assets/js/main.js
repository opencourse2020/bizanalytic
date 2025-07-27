(function ($) {    
    "use strict"

    $(document).ready(function () {

        // data background
        $("[data-background]").each(function () {
            $(this).css("background-image", "url(" + $(this).attr("data-background") + ")");
        });

        // mobile menu
        $('nav').meanmenu({
            meanMenuContainer: '.mobile-menu',
            meanScreenWidth: "991.98",
            onePage: false
        });

        // partner slide duplicate
        if ($('.partner-slider').length) {
            $('.partner-slider').append($('.partner-slider').html());
        }

        // counter up init
        $('.counter').counterUp({
            delay: 10,
            time: 1500
        });

        // service slider
        $('.service-slider').slick({
            slidesToShow: 3,
            slidesToScroll: 1,
            speed: 1200,
            autoplay: true,
            autoplaySpeed: 3000,
            infinite: true,
            dots: false,
            arrows: true,
            prevArrow: '<span class="prev-arrow"><i class="ri-arrow-left-line"></i></span>',
            nextArrow: '<span class="next-arrow"><i class="ri-arrow-right-line"></i></span>',
            responsive: [
                {
                    breakpoint: 1199.98,
                    settings: {
                        slidesToShow: 2,
                    },
                },
                {
                    breakpoint: 991.98,
                    settings: {
                        slidesToShow: 2,
                        arrows: false,
                    },
                },
                {
                    breakpoint: 767.98,
                    settings: {
                        slidesToShow: 1,
                        arrows: false,
                    },
                },
            ]
        });

        // testimonial slider
        $('.testimonial-slider').slick({
            slidesToShow: 1,
            slidesToScroll: 1,
            fade: true,
            speed: 1200,
            autoplay: true,
            autoplaySpeed: 2000,
            infinite: true,
            dots: true,
            arrows: false,
        });

        // project slider
        $('.project-slider').slick({
            centerMode: true,
            centerPadding: '200px',
            slidesToShow: 3,
            slidesToScroll: 1,
            speed: 1200,
            autoplay: true,
            autoplaySpeed: 2000,
            infinite: true,
            dots: false,
            arrows: false,
            responsive: [
                {
                    breakpoint: 1199.98,
                    settings: {
                        slidesToShow: 2,
                    },
                },
                {
                    breakpoint: 991.98,
                    settings: {
                        slidesToShow: 3,
                        centerMode: false,
                        centerPadding: '0',
                    },
                },
                {
                    breakpoint: 767.98,
                    settings: {
                        slidesToShow: 2,
                        centerMode: false,
                        centerPadding: '0',
                    },
                },
                {
                    breakpoint: 575.98,
                    settings: {
                        slidesToShow: 1,
                        centerMode: false,
                        centerPadding: '0',
                    },
                },
            ]
        });

        // accordion
        $('.accordion-header').on('click', function () {
            const $item = $(this).parent();
            const isActive = $item.hasClass('active'); 
            
            $('.accordion-item').removeClass('active');
            if (!isActive) {
                $item.addClass('active');
            }
        });

        // team slider
        $('.team-slider').slick({
            slidesToShow: 1,
            slidesToScroll: 1,
            fade: true,
            speed: 1200,
            autoplay: true,
            autoplaySpeed: 3000,
            infinite: true,
            dots: false,
            arrows: true,
            prevArrow: '<span class="prev-arrow"><i class="ri-arrow-left-line"></i></span>',
            nextArrow: '<span class="next-arrow"><i class="ri-arrow-right-line"></i></span>',
            responsive: [
                {
                    breakpoint: 991.98,
                    settings: {
                        arrows: false,
                    },
                },
            ]
        });

        // magnific popup init
        $(".popup-gallery").magnificPopup({
            delegate: '.popup-img',
            type: 'image',
            gallery: {
                enabled: true
            },
        });

        $(".popup-youtube, .popup-vimeo, .popup-gmaps").magnificPopup({
            type: "iframe",
            mainClass: "mfp-fade",
            removalDelay: 160,
            preloader: false,
            fixedContentPos: false
        });

        // post slider
        $('.blog-slider').slick({
            slidesToShow: 1,
            slidesToScroll: 1,
            fade: true,
            speed: 1200,
            autoplay: false,
            autoplaySpeed: 2000,
            infinite: true,
            dots: false,
            arrows: true,
            prevArrow: '<span class="prev-arrow"><i class="ri-arrow-left-line"></i></span>',
            nextArrow: '<span class="next-arrow"><i class="ri-arrow-right-line"></i></span>',
            responsive: [
                {
                    breakpoint: 575.98,
                    settings: {
                        arrows: false,
                    },
                },
            ]
        });

        // copyright date
        var date = new Date().getFullYear();
        $("#date").html(date);

    });

    $(window).on('scroll', function () {

        // navbar fixed
        const headerHeight = $(".header-top").outerHeight();
        if ($(this).scrollTop() > headerHeight) {
            $(".menu-area").addClass("fixed-top");
        } else {
            $(".menu-area").removeClass("fixed-top");
        }

        // back to top scroll
        var scrollTop = $('.back-to-top');
        if ($(window).scrollTop() > 1000) {
            scrollTop.fadeIn(1000);
        } else {
            scrollTop.fadeOut(1000);
        }

        // progress bar
        if ($('.progress-bar').length) {
            let scroll = $(window).scrollTop();
            let oTop = $('.progress-bar').offset().top - window.innerHeight;

            if (scroll > oTop) {
                $('.progress-bar').addClass('progressbar-active');
            } else {
                $('.progress-bar').removeClass('progressbar-active');
            }
        }

    });

    $(window).on('load', function () {

        // wow js
        new WOW().init();

        // preloader
        var preLoder = $("#preloader");
        preLoder.fadeOut(0);

        // back to top animate
        $(".back-to-top").on('click', function () {
            $("html").animate({
                "scrollTop": "0"
            }, 1000);
        });

    });

})(jQuery);
