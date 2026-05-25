FROM php:8.2-fpm-alpine

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN apk add --no-cache \
    git curl libpng-dev libzip-dev zip unzip \
    postgresql-dev oniguruma-dev icu-dev \
    freetype-dev libjpeg-turbo-dev libwebp-dev \
    supervisor nodejs npm

RUN docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp \
    && docker-php-ext-install \
    pdo pdo_pgsql pgsql mbstring zip exif \
    pcntl bcmath gd intl opcache

RUN pecl install redis && docker-php-ext-enable redis

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

RUN addgroup -g ${GROUP_ID} laravel \
    && adduser -D -u ${USER_ID} -G laravel laravel

WORKDIR /var/www/html

COPY php.ini /usr/local/etc/php/conf.d/custom.ini

RUN chown -R laravel:laravel /var/www/html

USER laravel

EXPOSE 9000

CMD ["php-fpm"]
