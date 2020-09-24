/********************************************************************************
** Form generated from reading UI file 'mainwindow.ui'
**
** Created by: Qt User Interface Compiler version 5.12.5
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_MAINWINDOW_H
#define UI_MAINWINDOW_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_MainWindow
{
public:
    QWidget *centralwidget;
    QHBoxLayout *horizontalLayout;
    QVBoxLayout *verticalLayout;
    QLabel *label_x;
    QLabel *label_y;
    QSpacerItem *verticalSpacer;
    QLabel *label_x_to;
    QLabel *label_y_to;
    QPushButton *GoButton;
    QPushButton *FotoButton;
    QWidget *widget;
    QVBoxLayout *verticalLayout_2;
    QPushButton *selectButton;
    QPushButton *zoomoffButton;
    QPushButton *zoominButton_3;
    QPushButton *zoomoutButton;
    QPushButton *moveButton;
    QSpacerItem *verticalSpacer_2;
    QStatusBar *statusbar;

    void setupUi(QMainWindow *MainWindow)
    {
        if (MainWindow->objectName().isEmpty())
            MainWindow->setObjectName(QString::fromUtf8("MainWindow"));
        MainWindow->resize(694, 456);
        centralwidget = new QWidget(MainWindow);
        centralwidget->setObjectName(QString::fromUtf8("centralwidget"));
        horizontalLayout = new QHBoxLayout(centralwidget);
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        verticalLayout = new QVBoxLayout();
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        verticalLayout->setSizeConstraint(QLayout::SetFixedSize);
        label_x = new QLabel(centralwidget);
        label_x->setObjectName(QString::fromUtf8("label_x"));
        QSizePolicy sizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(label_x->sizePolicy().hasHeightForWidth());
        label_x->setSizePolicy(sizePolicy);
        label_x->setMaximumSize(QSize(60, 16777215));

        verticalLayout->addWidget(label_x);

        label_y = new QLabel(centralwidget);
        label_y->setObjectName(QString::fromUtf8("label_y"));
        sizePolicy.setHeightForWidth(label_y->sizePolicy().hasHeightForWidth());
        label_y->setSizePolicy(sizePolicy);
        label_y->setMaximumSize(QSize(60, 16777215));

        verticalLayout->addWidget(label_y);

        verticalSpacer = new QSpacerItem(20, 40, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout->addItem(verticalSpacer);

        label_x_to = new QLabel(centralwidget);
        label_x_to->setObjectName(QString::fromUtf8("label_x_to"));

        verticalLayout->addWidget(label_x_to);

        label_y_to = new QLabel(centralwidget);
        label_y_to->setObjectName(QString::fromUtf8("label_y_to"));

        verticalLayout->addWidget(label_y_to);

        GoButton = new QPushButton(centralwidget);
        GoButton->setObjectName(QString::fromUtf8("GoButton"));
        sizePolicy.setHeightForWidth(GoButton->sizePolicy().hasHeightForWidth());
        GoButton->setSizePolicy(sizePolicy);

        verticalLayout->addWidget(GoButton);

        FotoButton = new QPushButton(centralwidget);
        FotoButton->setObjectName(QString::fromUtf8("FotoButton"));
        sizePolicy.setHeightForWidth(FotoButton->sizePolicy().hasHeightForWidth());
        FotoButton->setSizePolicy(sizePolicy);

        verticalLayout->addWidget(FotoButton);


        horizontalLayout->addLayout(verticalLayout);

        widget = new QWidget(centralwidget);
        widget->setObjectName(QString::fromUtf8("widget"));
        QSizePolicy sizePolicy1(QSizePolicy::Expanding, QSizePolicy::Expanding);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(widget->sizePolicy().hasHeightForWidth());
        widget->setSizePolicy(sizePolicy1);
        QPalette palette;
        QBrush brush(QColor(255, 255, 255, 255));
        brush.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Base, brush);
        QBrush brush1(QColor(253, 250, 255, 255));
        brush1.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Window, brush1);
        palette.setBrush(QPalette::Inactive, QPalette::Base, brush);
        palette.setBrush(QPalette::Inactive, QPalette::Window, brush1);
        palette.setBrush(QPalette::Disabled, QPalette::Base, brush1);
        palette.setBrush(QPalette::Disabled, QPalette::Window, brush1);
        widget->setPalette(palette);
        widget->setAutoFillBackground(true);

        horizontalLayout->addWidget(widget);

        verticalLayout_2 = new QVBoxLayout();
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        selectButton = new QPushButton(centralwidget);
        selectButton->setObjectName(QString::fromUtf8("selectButton"));
        sizePolicy.setHeightForWidth(selectButton->sizePolicy().hasHeightForWidth());
        selectButton->setSizePolicy(sizePolicy);
        selectButton->setMinimumSize(QSize(82, 0));

        verticalLayout_2->addWidget(selectButton);

        zoomoffButton = new QPushButton(centralwidget);
        zoomoffButton->setObjectName(QString::fromUtf8("zoomoffButton"));
        sizePolicy.setHeightForWidth(zoomoffButton->sizePolicy().hasHeightForWidth());
        zoomoffButton->setSizePolicy(sizePolicy);
        zoomoffButton->setMinimumSize(QSize(82, 0));

        verticalLayout_2->addWidget(zoomoffButton);

        zoominButton_3 = new QPushButton(centralwidget);
        zoominButton_3->setObjectName(QString::fromUtf8("zoominButton_3"));
        sizePolicy.setHeightForWidth(zoominButton_3->sizePolicy().hasHeightForWidth());
        zoominButton_3->setSizePolicy(sizePolicy);
        zoominButton_3->setMinimumSize(QSize(82, 0));
        zoominButton_3->setMaximumSize(QSize(82, 16777215));

        verticalLayout_2->addWidget(zoominButton_3);

        zoomoutButton = new QPushButton(centralwidget);
        zoomoutButton->setObjectName(QString::fromUtf8("zoomoutButton"));
        sizePolicy.setHeightForWidth(zoomoutButton->sizePolicy().hasHeightForWidth());
        zoomoutButton->setSizePolicy(sizePolicy);
        zoomoutButton->setMinimumSize(QSize(82, 0));
        zoomoutButton->setMaximumSize(QSize(82, 16777215));

        verticalLayout_2->addWidget(zoomoutButton);

        moveButton = new QPushButton(centralwidget);
        moveButton->setObjectName(QString::fromUtf8("moveButton"));
        sizePolicy.setHeightForWidth(moveButton->sizePolicy().hasHeightForWidth());
        moveButton->setSizePolicy(sizePolicy);
        moveButton->setMinimumSize(QSize(82, 0));
        moveButton->setMaximumSize(QSize(82, 16777215));

        verticalLayout_2->addWidget(moveButton);

        verticalSpacer_2 = new QSpacerItem(20, 40, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout_2->addItem(verticalSpacer_2);


        horizontalLayout->addLayout(verticalLayout_2);

        MainWindow->setCentralWidget(centralwidget);
        statusbar = new QStatusBar(MainWindow);
        statusbar->setObjectName(QString::fromUtf8("statusbar"));
        MainWindow->setStatusBar(statusbar);

        retranslateUi(MainWindow);

        QMetaObject::connectSlotsByName(MainWindow);
    } // setupUi

    void retranslateUi(QMainWindow *MainWindow)
    {
        MainWindow->setWindowTitle(QApplication::translate("MainWindow", "MainWindow", nullptr));
        label_x->setText(QApplication::translate("MainWindow", "x: ", nullptr));
        label_y->setText(QApplication::translate("MainWindow", "y: ", nullptr));
        label_x_to->setText(QString());
        label_y_to->setText(QString());
        GoButton->setText(QApplication::translate("MainWindow", "fahr", nullptr));
        FotoButton->setText(QApplication::translate("MainWindow", "Foto", nullptr));
        selectButton->setText(QApplication::translate("MainWindow", "Select", nullptr));
        zoomoffButton->setText(QApplication::translate("MainWindow", "\342\206\251\357\270\217", nullptr));
        zoominButton_3->setText(QApplication::translate("MainWindow", "zoom in", nullptr));
        zoomoutButton->setText(QApplication::translate("MainWindow", "zoom out", nullptr));
        moveButton->setText(QApplication::translate("MainWindow", "move", nullptr));
    } // retranslateUi

};

namespace Ui {
    class MainWindow: public Ui_MainWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_MAINWINDOW_H
